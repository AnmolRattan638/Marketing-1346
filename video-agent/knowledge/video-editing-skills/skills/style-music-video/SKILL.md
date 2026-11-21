---
name: style-music-video
description: Music video editing style - performance and narrative music videos, lyric/visualizer videos and song-led montages - cutting on bar and phrase structure, multi-take performance sync, energy mapping to song sections, effects on drops, lip-sync accuracy, and creative techniques (strobe, double exposure, glitch, color shifts per section). Use when editing to a full song or for an artist, band, or song promo.
---

# Style: Music video

Load with: `beat-sync`, `editing-foundations`, `color-grading`, `ffmpeg-pipeline` (+ `style-kinetic-typography` for lyric videos).

## Signature

- Song structure drives the edit: intro / verse / pre-chorus / chorus / bridge / outro, each with its own visual treatment.
- Cuts on bars (every 1, 2 or 4 beats) in verses; faster (beats or 8ths) in choruses; one long held shot somewhere for contrast.
- Performance takes synced to the master track, intercut with narrative/B-roll.
- Drops get the biggest visual (new location, effect, slow-mo, colour change).

## Workflow

1. Get the master audio; run `beats.py`; mark sections (energy curve + listening notes from the user).
2. **Sync performance takes**: each take was shot to playback. Align by cross-correlating the take's scratch audio with the master (`scipy.signal.correlate` on onset envelopes); verify lip-sync on a few frames (± 1 frame).
3. Make a section plan: shot types, colour/look per section, pace per section.
4. Assemble a "best performance" spine, then cut in narrative/B-roll on bars.
5. Effects per section: e.g. verse clean; chorus with flashes on snares; bridge slow-mo + double exposure; final chorus everything + faster cuts.
6. Grade: allow a distinct look per section, consistent within it.
7. Master audio is untouched (the label/artist master); don't normalise a mastered song.

## Techniques

- **Strobe/stutter**: repeat 2-4 frames on a fill or stutter in the song.
- **Double exposure**: `blend=all_mode=screen` of performer over landscape.
- **Speed shooting trick**: if footage was shot at 2x playback speed for slow-mo lip-sync, conform to 50%.
- **Visualizer**: `showwaves`/`showspectrum`/`avectorscope` from ffmpeg as stylised layers; or audio-reactive params (RMS → scale/glow).
- **Lyric video**: see `style-kinetic-typography`.

## Quality bar

Lip-sync within one frame on every performance shot; no cut misses a bar it is meant to hit; the drop is the visual peak.
