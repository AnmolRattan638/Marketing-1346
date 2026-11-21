---
name: sound-design
description: Sound design and audio finishing for video edits - music editing (cutting songs on bars, loops, stingers), SFX placement on visible events (whooshes, hits, risers, clicks, impacts, braams), aligning SFX attacks to frames, synthesizing simple SFX, dialogue cleanup, ducking music under speech, J/L-cut audio, room tone, stereo placement, and loudness mastering (-14 LUFS, true peak). Use whenever an edit has music, voice, or sound effects.
---

# Sound design

Scripts in `scripts/`:
- `sfx.py OUTDIR` — synthesizes a starter kit of royalty-free SFX (whoosh up/down, hit/thud, riser, tick/click, pop, sub boom, glitch) as 48 kHz WAVs.
- `mix.py plan.json out.wav` — places music + SFX + dialogue on a timeline with gains, fades, pan and sidechain ducking, then normalises.

## 1. Principles

- **Sound sells the cut.** A whoosh on a whip, a thud on an impact, a click on a UI tap make visuals feel heavier.
- **Fewer, better effects.** Tie each effect to something visible. ~6-10 well-timed effects in a 20 s reel read as designed; 25 read as cheap.
- **Hit on the frame.** Most SFX have a pre-attack (whoosh build). Measure the attack (first sample above -30 dBFS of the peak, or the peak for whooshes) and start the file that much **before** the visual contact frame.
- **Music edit points**: cut music on bar lines (every 4 beats), crossfade 10-50 ms at cuts; hide edits under a hit, a cymbal, or a whoosh.
- **Silence is a tool**: 0.2-0.5 s of silence (or a low-pass dip) before a drop or punchline makes it hit harder.

## 2. SFX vocabulary

| Effect | Use on |
|---|---|
| Whoosh / swish | whip pans, slides, fast zooms, text flying in |
| Riser (noise/tonal sweep up) | build into a drop, reveal, title |
| Hit / impact / boom | smash cuts, logo hit, drop, title slam |
| Braam / sub drop | trailer moments, reveals |
| Click / tick / pop | UI taps, text pop-ins, counters, bubbles |
| Glitch / digital stutter | glitch transitions, tech edits |
| Camera shutter / film | photo stills, freeze frames |
| Record scratch / rewind | meme pause, "wait, let me explain" |
| Ambience / room tone | under everything to avoid dead silence |
| Foley (footsteps, cups, keys) | ASMR/aesthetic edits, product shots; re-record or synthesize |

Free sources: user-provided, Pixabay sound effects, Freesound (check each licence: CC0 vs CC-BY attribution), YouTube Audio Library, or synthesize (`sfx.py`). Record source + licence in `CREDITS.md`.

## 3. Levels (starting points, then measure)

- Dialogue: peaks ~-6 to -3 dBFS before mastering; dialogue is the loudest consistent element.
- Music under dialogue: duck 12-18 dB below its music-only level; attack 50-150 ms, release 300-600 ms.
- Music-only sections: full level, -14 LUFS integrated for the whole piece after mastering.
- SFX: just audible above music; impacts can peak with the music, whooshes 6-10 dB under.
- Pan subtle effects with movement (left-to-right whip → pan -0.4 → +0.4).

ffmpeg sidechain duck: 
```bash
[music][voice]sidechaincompress=threshold=0.03:ratio=8:attack=50:release=400[ducked]
```
(Use a split copy of the voice as the sidechain, then `amix` the ducked music with the voice.)

## 4. Dialogue cleanup (ffmpeg)

- High-pass 80 Hz: `highpass=f=80`
- Noise reduction: `afftdn=nr=12:nf=-40` (gentle); for heavy noise use RNNoise `arnndn=m=model.rnnn`, or Resolve Voice Isolation / Adobe Enhance.
- De-ess: `deesser`
- Compression: `acompressor=threshold=-18dB:ratio=3:attack=10:release=150`
- 10-30 ms fades at every dialogue cut; room tone under gaps.

## 5. Mastering

Two-pass loudnorm on the final mix (see `ffmpeg-pipeline/scripts/export.py --loudnorm`):
- Social (IG/TikTok/Shorts/YouTube): -14 LUFS integrated, true peak ≤ -1 dBTP.
- Podcast/voice-led YouTube: -16 LUFS.
- Broadcast (EBU R128): -23 LUFS; US ATSC A/85: -24 LKFS.
Measure per section too (`ebur128` momentary): an end card 15 dB quieter than the body, or SFX louder than speech, is a bug.

## 6. Licensing reality

- Trending sounds in Instagram/TikTok are licensed only inside the app. For a reel that uses a trending sound, export **without** music (or with a guide track) and add the sound in-app, aligned to the same start point.
- Commercial/brand content: only use music licensed for commercial use.
- Never claim a mix "sounds good": you can only measure it. Ask the user to listen.
