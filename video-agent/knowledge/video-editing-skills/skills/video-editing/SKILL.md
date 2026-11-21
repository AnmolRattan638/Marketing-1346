---
name: video-editing
description: Master router for all video editing work. Use whenever the user asks to edit, cut, trim, grade, caption, subtitle, beat-sync, add music or SFX, add motion graphics, titles, text overlays, transitions, VFX or 3D to a video, reel, short, vlog, ad, trailer, music video or carousel, or names an editing style (cinematic, motion graphics, Instagram reel, velocity, talking head, documentary, kinetic typography, etc.). Picks the editing style, loads only the needed skills from this pack, and enforces the shared workflow and quality gates.
---

# Video editing (router)

This skill is the entry point of the **video-editing-skills** pack. It does three things:

1. Decides **which editing style** the job is (or asks, if the request is ambiguous).
2. Loads **only the skills that style needs** (each one is a separate skill in this pack).
3. Enforces the **shared workflow and the hard rules** that make every edit correct.

Do not load every skill. Load the style skill plus the 2-4 foundation skills it lists.

## Step 1 — inspect before deciding

Run these before proposing anything:

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,pix_fmt,color_transfer,color_primaries:stream_tags=rotate -of json INPUT
```

Note per source: duration, resolution, orientation (rotation tag / side data), fps (VFR phone footage is common), codec, bit depth, HDR transfer (`arib-std-b67` = HLG, `smpte2084` = PQ), audio channels.

Also look for existing project files and prefer the tool the project already uses:

| Found in project | Use |
|---|---|
| `.drp`, Resolve running, `mcp__davinci-resolve__*` tools available | `davinci-resolve` skill |
| `package.json` with `remotion` | Remotion (upstream `remotion-dev/skills`) + `motion-graphics` style |
| `hyperframes.json` / HyperFrames project | HyperFrames (upstream `heygen-com/hyperframes`) |
| Only raw clips | Python + ffmpeg + PIL/OpenCV pipeline (`ffmpeg-pipeline`) |
| A reference video ("make it like this") | `reference-matching` first |

## Step 2 — pick the style

| Style skill | Use for | Signature |
|---|---|---|
| `style-instagram-reels` | IG Reels, TikTok, YouTube Shorts | 9:16, hook in first 1 s, beat cuts, captions in safe zone |
| `style-velocity-edit` | "edit audio" trend, car/gym/anime/sports edits | speed ramps on hits, flashes, shakes, RGB split |
| `style-cinematic` | cinematic travel, brand films, short films | 24 fps, 2.39:1 or 9:16 film look, J/L cuts, filmic grade, grain |
| `style-motion-graphics` | animated titles, logo stings, lower thirds, UI animation | keyframed shapes/type, easing, design system |
| `style-kinetic-typography` | lyric videos, quote reels, word-by-word text | text is the picture; type moves on beat/word |
| `style-talking-head` | YouTube, podcasts, educators, creator videos | jump cuts on silence, punch-ins, B-roll, bold captions |
| `style-documentary` | interviews, mini-docs, case studies | story arc, interview + B-roll, natural captions, restraint |
| `style-music-video` | performance, lyric, visualizer edits | cut on bar structure, performance coverage, effects on drops |
| `style-vlog-travel` | day-in-life, travel montage, vlogs | match cuts, whip transitions, ambient sound, location titles |
| `style-commercial-promo` | product, restaurant, real estate, brand ads | hook, benefit beats, product hero shots, CTA end card |
| `style-explainer` | tutorials, product demos, screen recordings, SaaS launch | zoom-ins on UI, callouts, cursor focus, clean narration |
| `style-trailer` | trailers, teasers, "story as trailer" reels | title cards, risers + hits, black frames, escalating pace |
| `style-vfx-compositing` | tracking text/graphics to objects, green screen, 3D/hologram | planar/point tracking, keying, glow, match grade |
| `style-aesthetic-minimal` | calm lifestyle, "aesthetic" reels, slow living | lowercase serif captions, soft grade, long holds, grain |
| `style-meme-comedy` | memes, comedy skits, reaction edits | zoom punches, freeze frames, SFX, impact captions |
| `style-event-highlight` | weddings, concerts, conferences, sports recaps | story by music, speeches as L-cuts, emotional peaks |
| `style-instagram-carousel` | IG carousel / photo dumps / "week in frames" | 4:5 stills, consistent grade, cover hook, text hierarchy |
| `reel-hand-text` | trending hand-lettered quote stack on a reel | stacked curved hand-drawn capitals |

If two styles fit, pick the dominant one and borrow techniques from the other. If none fits, combine foundations and say so.

## Step 3 — load foundations the style needs

| Foundation skill | What it owns |
|---|---|
| `editing-foundations` | cut types, pacing, shot grammar, continuity, story structures |
| `ffmpeg-pipeline` | probing, HDR/rotation fixes, per-segment render, concat, overlays, export specs |
| `beat-sync` | beat/onset detection, beat grids, cutting and ramping on hits, speed ramps |
| `color-grading` | CDL mental model, LUTs, looks, log/HDR transforms, skin tones, matching shots |
| `captions-typography` | caption styles, word-level timing, fonts, safe zones, ASS/PIL rendering |
| `sound-design` | music edit, SFX placement, ducking, loudness mastering |
| `motion-tracking` | camera motion analysis, stabilization, point/planar tracking, keying |
| `reference-matching` | measure a reference video (cuts, text timing, grade, pace) and reproduce it |
| `shoot-planning` | shot lists, storyboards, camera settings before the shoot |
| `davinci-resolve` | doing the edit inside DaVinci Resolve (UI, scripting API, MCP tools) |

## Step 4 — the shared workflow (every style)

1. **Inventory**: probe sources, watch key frames (`ffmpeg -ss T -i IN -frames:v 1 f.png`), transcribe speech word-level if there is dialogue, detect beats if there is music.
2. **Ask only what the material can't answer**: platform + aspect, target length, music (user-supplied or to find), brand fonts/colours, must-keep moments, reference video.
3. **Propose a plan in plain English** (4-8 sentences: structure, music, cut rhythm, grade, text, transitions, length). **Wait for confirmation** before rendering the final.
4. **Build as a script** (e.g. `edit/build.py`) that regenerates the whole output from sources. Keep decisions in data files (`edl.json`, `timing.json`, `text_layout.json`) so feedback = edit data + re-run.
5. **Render a fast preview** (720p / CRF 28 / `-preset veryfast`) and **self-check** (see Quality gates).
6. **Iterate** on feedback; never re-transcribe or re-analyse unchanged sources (cache).
7. **Final render** to the platform spec, then write a short log (`edit/project.md`): decisions, files, open issues.

## Hard rules (correctness, not taste)

1. Never cut inside a spoken word. Snap to word boundaries, pad 30-200 ms.
2. 10-30 ms audio fades at every hard audio cut (no clicks).
3. Fix rotation and HDR before anything else (HLG/PQ phone footage tone-mapped to SDR Rec.709 unless delivering HDR).
4. Encode lossy only once at the end. Intermediates: lossless/visually lossless (`-crf 0`..`10`, ProRes, or PNG frames).
5. Subtitles/captions are composited last, above every overlay.
6. Every text element sits inside the platform safe zone.
7. Fonts are loaded from an explicit file path (or asserted loaded in a browser). Never trust a silent fallback.
8. Never use linear easing on motion; use ease-out for arrivals, ease-in for exits, ease-in-out for moves.
9. Every cut that is meant to be on a beat lands on the frame nearest the beat (`round(t*fps)`), verified.
10. Never invent facts in on-screen text (prices, addresses, phone numbers, stats). Use only what the user gave.
11. Measure, don't claim: report loudness (LUFS / true peak), duration, resolution, fps from `ffprobe`/`ebur128`. You cannot hear or watch in real time; say so.

## Quality gates (before showing the user)

- Grab frames at every cut ±2 frames, first/last second, every text-on moment. Look for flashes, black frames, wrong frames, text clipping, text over faces.
- `ffprobe` output: duration, fps, resolution, codec, pix_fmt `yuv420p`, audio 48 kHz.
- `ffmpeg -i out.mp4 -af ebur128=peak=true -f null -` → integrated around -14 LUFS (social) or -16 (YouTube talk), true peak ≤ -1 dBTP.
- Check the brightest and darkest frames still hold text contrast.
- Cap self-fix loops at 3; then report remaining issues honestly.

## Upstream skills this pack works with (optional)

These are separate projects, installed with their own commands. Use them when present:

- Remotion: `npx skills add remotion-dev/skills`
- HyperFrames (HTML → video): `npx skills add heygen-com/hyperframes`
- video-use (transcript-driven cutting, ElevenLabs Scribe): https://github.com/browser-use/video-use

Tell the user in one line which style and skills you picked, then work.
