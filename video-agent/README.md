# video-agent

Personal daily short-video agent. Groq writes the plan, Pexels gives footage, Kokoro/edge-tts does the voice, Whisper times the captions, Remotion renders, Telegram receives the result. Runs on GitHub Actions, no PC or GPU needed.

## Setup (10 min)

1. Create a new private GitHub repo and push this folder.
2. Repo → Settings → Secrets and variables → Actions → add:
   `GROQ_API_KEY`, `PIXABAY_API_KEY` (free, instant; used while Pexels is not issuing keys) and/or `PEXELS_API_KEY`, optional extra fallbacks `COVERR_API_KEY` (video, after Pexels/Pixabay) and `UNSPLASH_ACCESS_KEY` (photos, after Pixabay/Pexels), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   (secrets are per repo, so re-add them even if Marketing-1346 has them).
3. Run `cd template && npm install` once locally or in a Codespace and commit `package-lock.json` (already included in the zip).
4. Edit `topics.txt` (one topic per line, picked by date) and `config.json` (language `en` or `hi`, voice, brand notes).
5. Actions → "Daily video" → Run workflow. Tick `offline` first to test the pipeline without any API.

## How it works

`agent/run.py` → `plan.py` (Groq JSON plan, validated, one retry) → per scene: `footage.py`, `voice.py`, `captions.py`, `sfx_plan.py` → `manifest.py` → `render.py` (Remotion, template in `template/`) → `notify.py` (Telegram).

Skills in `skills/` are plain markdown loaded into the Groq prompt (`planner-rules.md`, `sfx-notes.md` by default; others via `extra_skills` in config). Put your own music in `assets/music/`, replace the synthesized SFX in `assets/sfx/` (same file names), drop hand-made hero clips in `assets/hero/`.

## Local run

```
pip install -r requirements.txt
bash scripts/make_sfx.sh
cd template && npm install && cd ..
python -m agent.run --offline        # no keys needed
python -m agent.run --topic "..."    # real run, needs the env vars from .env.example
```

## Tested vs not tested

Tested in a sandbox: Python compiles, TypeScript typechecks, `--offline` renders a 1080x1920 mp4 with audio and animated captions.

NOT tested (no keys or network access in the sandbox): Groq planning and Whisper calls, Pexels download, Kokoro and edge-tts voices, Telegram sending, the GitHub Actions workflow itself (apt package list for Chrome may need tweaking). Groq model names, Kokoro voice names and Hindi voices are from memory; check them if a call errors.

## Not built yet

- Lottie overlays, colour grade/LUT, editly fallback renderer
- Telegram approve → post step (v1 only sends the video; wire into Marketing-1346's approval flow later)
- GPU-based generation (Wan, MusicGen, AudioLDM); AudioLDM is non-commercial licensed
- After Effects repos: reference only, they need paid AE
- Footage order: your own hero clips, Pexels, Pixabay, then a plain placeholder. Pixabay has no portrait filter, so its clips are centre-cropped to 9:16. Keep `credits.json` per run; check Pexels licence terms before posting commercially

## Your cloned voice (Chatterbox, open source, MIT)
`agent/voice.py` can speak every reel in your own voice. The reference clip is never committed (the repo is public): put it in the secret `VOICE_REF_B64` (base64 of a 10-15 s clip). Run Actions -> "Voice test (your cloned voice)" first: it sends three test lines (Hindi, Roman Hinglish, English) to Telegram with how long each took. If you like them, set `"voice_engine": "chatterbox"` in `config.json`. If your voice fails for any reason, the chain falls back to Kokoro and then edge-tts, so a reel is never blocked.

## Hybrid editing from your `edits` folder (strict)
Put one folder in Google Drive, share it as "Anyone with the link", and add its link as the repo secret `EDITS_DRIVE_URL`:
```
edits/
  hero/   finished reels you like (the agent measures their cut rhythm) + optional notes.txt
  raw/    your recordings, demos, screen captures and photos + optional notes.txt
```
- **hero/notes.txt** (all lines optional): `shot_seconds: 1.6-3.0`, `transitions: cut 80, fade 20`, `punch_in: 30`, `first_shot: raw`. Measured automatically from the reels: shot length and cut rhythm only. Transitions and effects are NOT detected from video; the allowed ones are cut, fade, punch_in, push_in and Ken Burns on photos.
- **Which clip belongs to which service (explicit labels only, never guessed):** put clips in `raw/<service>/` (`website`, `chatbot`, `animated_ads`, `lead_gen`, `reel_scripts`, `seo_blogs`) or `raw/general/` for clips that fit any service. Alternatives: start the file name with the service id (`chatbot_phone.mp4`) or add `service=chatbot` to its notes.txt line. A file with no label is ignored and reported in the log. A reel only ever uses clips of its own service plus `general`; if there are none for that service, no reel is made. The reel's service comes from `[chatbot] topic text` in topics.txt, otherwise from keywords in `config.json` -> `services`, otherwise `general` (a tie is `general`, never a guess).
- **raw/notes.txt**: lines like `IMG_2031.jpg: service=general, me at my desk with a laptop`. File names count as tags too, so name clips `website_demo.mp4`, `chatbot_demo.mp4`.
- Every narrated scene is cut into shots and each shot is your raw clip, a stock clip or a photo. The code (agent/hybrid.py) picks the source, the model never does. Rules, checked again on the finished reel: at least 1 raw shot (`min_raw_shots`; each raw shot is the best-scoring part of one of your 5-10 s clips, never the whole file, and a clip is reused with different parts; with 2+ clips at least 2 are used), at most 45% stock, photos are mixed in but never forced (`min_photo_shots` defaults to 0), no source 3 times in a row, the first shot is yours, shot lengths stay inside your Hero range. In strict mode a broken rule or a missing/empty raw folder stops the run and Telegram says why. Tune in `config.json` -> `hybrid`; `"enabled": false` returns to one stock clip per scene.
- Limits: Drive downloads fail above 50 files per folder or when the link is not public; clips are matched to scenes by file-name tags, not by what is on screen.
