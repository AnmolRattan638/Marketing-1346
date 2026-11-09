# video-agent

Personal daily short-video agent. Groq writes the plan, Pexels gives footage, Kokoro/edge-tts does the voice, Whisper times the captions, Remotion renders, Telegram receives the result. Runs on GitHub Actions, no PC or GPU needed.

## Setup (10 min)

1. Create a new private GitHub repo and push this folder.
2. Repo → Settings → Secrets and variables → Actions → add:
   `GROQ_API_KEY`, `PEXELS_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
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
- Pexels clips: keep `credits.json` per run; check Pexels licence terms before posting commercially

## Your cloned voice (Chatterbox, open source, MIT)
`agent/voice.py` can speak every reel in your own voice. The reference clip is never committed (the repo is public): put it in the secret `VOICE_REF_B64` (base64 of a 10-15 s clip). Run Actions -> "Voice test (your cloned voice)" first: it sends three test lines (Hindi, Roman Hinglish, English) to Telegram with how long each took. If you like them, set `"voice_engine": "chatterbox"` in `config.json`. If your voice fails for any reason, the chain falls back to Kokoro and then edge-tts, so a reel is never blocked.
