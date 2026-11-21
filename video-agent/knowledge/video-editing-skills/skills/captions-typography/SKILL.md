---
name: captions-typography
description: Captions, subtitles and on-screen text for video - word-level transcription, caption styles (bold pop / Hormozi, karaoke word highlight, natural sentence, minimal lowercase, hand-lettered, cinematic lower third, title cards), chunking and timing rules, font pairing, sizes for phone viewing, contrast, platform safe zones, and rendering with ASS subtitles, PIL overlays or HTML. Use whenever a video needs captions, subtitles, titles, quotes or any text on screen.
---

# Captions and typography

Script: `scripts/captions.py words.json out.ass --style pop|karaoke|sentence|minimal [--size 1080x1920]`
Turns word-level timestamps (`[{"word","start","end"}]`) into a styled ASS file; burn with `-vf subtitles=out.ass:fontsdir=fonts`.

## 1. Get word-level timing

- Best: a hosted ASR with word timestamps and verbatim fillers (ElevenLabs Scribe, Deepgram, AssemblyAI) or local `faster-whisper`/`whisperx` with `word_timestamps=True` (whisperx aligns better).
- DaVinci Resolve Studio: Timeline → Create Subtitles from Audio, then export SRT (phrase-level only).
- Always keep word-level JSON as the source of truth; SRT phrase files lose the gaps.
- Proofread names, brand words and numbers; ASR mangles them. Never "correct" what was said into something else.

## 2. Caption styles

| Style | Look | Chunking | Best for |
|---|---|---|---|
| **pop** (Hormozi/bold) | heavy sans (Montserrat ExtraBold, Anton, The Bold Font), UPPERCASE, thick outline or shadow, active word coloured (yellow/green) and scaled 110% | 1-3 words | talking-head reels, podcasts clips |
| **karaoke** | full line visible, current word highlighted as spoken | 4-7 words | lyric videos, tutorials |
| **sentence** | sentence case, medium weight, soft shadow or translucent box | 5-10 words, 1-2 lines | documentary, interviews, YouTube |
| **minimal** | lowercase, small serif or light sans, no outline, subtle shadow | phrase | aesthetic / calm reels |
| **hand-lettered** | stacked curved hand-drawn capitals (see `reel-hand-text`) | static quote | quote reels |
| **cinematic lower third** | name in medium caps + role in light, thin line accent | n/a | interviews, docs |

Rules for all:
- Minimum on-screen time ~0.3-0.35 s per chunk (merge short words with neighbours rather than flash).
- Break on punctuation and pauses ≥ 0.3 s; never split a name or number across chunks.
- Caption appears **with** the first syllable (not before) and disappears at the end of the last word + 0.1-0.2 s, or when the next appears.
- Max ~32-42 characters per line for 16:9; ~16-22 for 9:16 big-text styles.
- Captions are composited **last**, above all overlays.

## 3. Sizes for phones (1080-wide 9:16 canvas)

| Element | Size |
|---|---|
| Bold pop captions | 70-100 px cap-height-ish (font size 80-120) |
| Sentence captions | 48-60 px |
| Hook headline (first 2 s) | 90-140 px, max 2-3 lines |
| Lower third name | 44-56 px |
| Small labels | ≥ 36 px (smaller is unreadable after compression) |

Scale linearly for 4K (×2). Outline 3-6 px at 1080w; shadow blur 6-12 px at 40-60% opacity.

## 4. Safe zones (9:16, 1080x1920)

- Top ~220-250 px: status bar, account name.
- Bottom ~350-420 px: caption text, audio label, buttons. Reels UI is tallest; TikTok similar; Shorts slightly less.
- Right ~120-140 px: like/comment/share column.
- Keep all text in about **x 60-940, y 250-1500**. Captions usually sit centred around y ≈ 1150-1350 (lower-middle), or y ≈ 700-900 when the bottom is busy.
- Faces: never cover eyes/mouth; move captions above or below the face per shot if needed (track the face, or set per-segment positions).
- 4:5 feed crop: the reel grid/profile shows a centre 1080x1350 crop and the profile grid a 3:4 crop; keep the hook text inside the centre.

## 5. Fonts

- Always load fonts by file path (PIL `ImageFont.truetype(path, size)`, ASS `fontsdir`). A missing font silently becomes Arial.
- Free, licensable (OFL) workhorses: Montserrat, Inter, Poppins, Anton, Bebas Neue, Oswald, Archivo Black (bold sans); Playfair Display, Cormorant Garamond, Lora, DM Serif (serif); Caveat, Great Vibes, Pacifico (script/hand); JetBrains Mono, IBM Plex Mono (code/tech).
- Pairing: one display face + one text face, max two families. Weight and size create hierarchy, not more fonts.
- Tracking: wide tracking (+5-15%) on small caps labels; tight (-1 to -3%) on huge headlines.

## 6. Contrast and readability

- Text over moving footage needs one of: outline, drop shadow, translucent box (black 40-60%), or a local darken (gradient behind text).
- Check text over the brightest frame in its window. If it fails, raise shadow first, then add a box; change colour last.
- White and yellow (#FFD400) are the most legible on varied footage; brand colours go on the active word, not the whole caption.

## 7. Animation of text

- Pop-in: scale 80% → 105% → 100% over 4-6 frames (ease-out back), opacity 0 → 1 in 2-3 frames.
- Word highlight: colour switch at word start; optional 105% scale.
- Typewriter: centre on the **full** string width so text doesn't slide as it types.
- Exits: faster than entrances (3-4 frames) or simply cut with the next chunk.
- Never linear easing.

## 8. Rendering paths

- **ASS via libass** (`captions.py`): fast, styled outlines/shadows, karaoke `\k` tags, positioning `\pos`, per-word colour `{\c&H00D4FF&}`. ASS colours are `&HAABBGGRR` (alpha, blue, green, red).
- **PIL frames / PNG overlays**: full control (curved text, gradients, glow, per-letter jitter); pipe frames into ffmpeg. See `reel-hand-text`.
- **HTML/CSS (HyperFrames/Remotion)**: best for complex kinetic type; assert fonts loaded before rendering.

## 9. Verify

Grab a frame in the middle of every caption chunk at phone size (scale to 360 px wide) and read it. Check none touch the safe-zone edges, none cover faces, and timings line up with speech (± 2 frames).
