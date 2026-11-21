---
name: style-talking-head
description: Talking-head / creator editing style for YouTube videos, podcasts, educational content and short clips - transcript-driven cutting, jump cuts on silences and filler removal, punch-in zooms to hide cuts and add emphasis, B-roll and screen inserts every few seconds, bold animated captions, sound-effect accents, emphasis text, chapter cards, and multi-cam podcast switching. Use for YouTube creator edits, podcast clips, course videos, vlogs to camera, or "edit like Ali Abdaal / Hormozi / MrBeast style".
---

# Style: Talking head (creator / YouTube / podcast)

Load with: `captions-typography`, `sound-design`, `ffmpeg-pipeline`, `editing-foundations`. Upstream `video-use` is excellent for transcript-driven cutting if installed.

## Signature

- **Tight**: silences, ums, false starts and retakes removed; pace 150-180 wpm feel.
- **Jump cuts** hidden or made rhythmic with **punch-ins** (alternate 100% / 110-120% scale, centred on the face).
- **Pattern interrupt every 3-8 s**: B-roll, zoom, text pop, graphic, angle change, SFX.
- **Captions**: bold pop style for shorts; sentence style (or none) for long-form YouTube.
- **Emphasis**: key words as big text, punch-in on the punchline, sound accent.
- **Structure**: hook (≤ 15 s for long-form, ≤ 2 s for shorts) → promise → content in chapters → payoff → CTA.

## Cut workflow

1. Transcribe word-level with fillers verbatim; cache.
2. Mark keep/remove in a text view (phrase per line with times).
   - Remove: silences > 0.3-0.5 s (keep ~0.1-0.2 s breathing room), fillers (um, uh, like, you know) unless natural, retakes (keep the last good take), tangents.
   - Never cut inside a word; pad 30-80 ms (fast) to 100-200 ms (calm).
3. Build the EDL; render per segment with 10-30 ms audio fades.
4. Punch-ins: every 2nd-4th cut, or on emphasis. Scale 1.1-1.2 centred on the face (detect face box once per segment with OpenCV/MediaPipe). Keep the eyes on the upper third.
5. B-roll plan: list sentences that describe something visual → insert B-roll/screen recordings/memes there (L-cut the voice over them).
6. Captions last.

## Podcast multi-cam

- Cut to the speaker within 0.3-0.5 s after they start (or on the first word for fast pace); reaction shots on laughs.
- Wide shot every 20-40 s to reset geography.
- Detect speaker by per-mic RMS (louder mic = active speaker), smooth with 1 s minimum shot length.
- Clips for shorts: find 30-60 s segments with a self-contained hook-to-payoff arc; reframe 16:9 → 9:16 on the active face.

## Audio

- Voice chain: high-pass 80 Hz → noise reduction → de-ess → compressor 3:1 → loudness -16 LUFS (YouTube voice) or -14 (shorts).
- Music bed 18-25 dB under voice, swells only in pauses and chapter breaks.
- Whoosh on B-roll entrances, pop on text, subtle riser into the payoff.

## Quality bar

- No audible clicks/breath fragments at cuts (check waveform around each cut).
- Punch-ins never crop the top of the head awkwardly or cut off hands in gesture.
- No caption covering the mouth.
- Retention test: does every 10 s window contain a new visual or idea?
