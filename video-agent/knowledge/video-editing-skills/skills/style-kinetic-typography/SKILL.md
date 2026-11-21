---
name: style-kinetic-typography
description: Kinetic typography editing style - text is the main visual - lyric videos, quote reels, word-by-word speech visualisation, typographic intros and ads - with words timed to syllables or beats, size and weight hierarchy for emphasis, masks and reveals, camera moves through type, and text locked to footage. Use when the user wants animated words, lyric video, word-by-word captions as the design, or a text-driven reel.
---

# Style: Kinetic typography

Load with: `captions-typography`, `beat-sync`, `style-motion-graphics` (principles), engine (HyperFrames/Remotion/PIL).

## Signature

- Words appear exactly on their spoken/sung syllable (word timestamps) or on beats.
- Hierarchy: key words big/bold/accent colour; filler words small/light. Size encodes emphasis.
- Layout changes per phrase: stacked, rotated 90°, scaled to fill width, split across lines.
- Motion follows meaning: "rise" moves up, "fall" drops, "stop" freezes, "shake" shakes.
- Limited palette (2-3 colours), 1-2 typefaces in several weights.
- Background: solid, gradient, subtle texture, or footage dimmed/blurred behind.

## Timing data

- Speech/lyrics: word-level transcript (ASR with word timestamps; for songs, run on the isolated vocal stem if possible — Demucs/UVR — and correct by hand).
- Save as `words.json`; every animation reads from it so audio and type cannot drift.
- Beat-driven: snap phrase changes to downbeats, words to beats or 8ths.

## Animation menu

| Move | Use |
|---|---|
| Mask rise (word slides up from baseline behind a mask) | default reveal, elegant |
| Scale pop (0.8 → 1.05 → 1.0) | emphasis words |
| Typewriter | code, terminal, messaging |
| Letter stagger (40-60 ms) | titles, slow lines |
| Blur-in (blur 12 → 0 + opacity) | soft/aesthetic |
| Swap / slot machine | changing one word repeatedly |
| Camera pan/zoom across a large type layout | continuous lyric flow |
| Glitch | tech, aggressive |
| Kerning squeeze / tracking expand | tension / release |

## Rules

- Readable at 1x speed on a phone: hold each word ≥ 0.25 s; a full line long enough to read (~0.3 s/word).
- Never more than ~7 words on screen in vertical formats.
- Line breaks by meaning, not by width.
- Contrast ≥ 4.5:1 against the background (dim/blur footage behind text by 30-50% if needed).
- Text locked to footage (on a surface or object): track it (see `motion-tracking`).
- Keep the active word position stable for the eye; move the layout between phrases, not mid-word.

## Real example

"I [M]iss you": the text's capital M was replaced by the M logo on an energy-drink can in the shot. The words were laid out in a coordinate system measured from the logo (centre, angle 119°, cap height) and mapped to the frame with an affine transform, tracked per frame by template matching, with letter in/out SFX synthesized to match. The footage was never moved; the text adapted to it.
