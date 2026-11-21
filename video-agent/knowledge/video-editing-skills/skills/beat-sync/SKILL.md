---
name: beat-sync
description: Sync an edit to music - beat, downbeat and onset detection with librosa, building a beat grid, choosing a song window, placing cuts, flashes, text and zooms on hits, speed ramps and velocity time-maps, measuring cut timing from a reference reel, and verifying every cut lands on the beat frame. Use for any music-driven edit (reels, montages, velocity edits, music videos, trailers, promos).
---

# Beat sync

Scripts in `scripts/`:
- `beats.py MUSIC --out beats.json [--start S --end E]` — tempo, beats, downbeat guess, strong onsets (hits), RMS energy per second.
- `timemap.py` — build a variable-speed time-map (speed ramps) and render it frame-by-frame with ffmpeg.

## 1. Analyse the music

```bash
python beats.py song.mp3 --out edit/beats.json
```
Outputs `tempo`, `beats` (s), `downbeats` (every 4th beat from the strongest phase), `hits` (strong onsets: snare/kick/drops), `energy` per 0.5 s.

Reading the result:
- Beat period `P = 60 / BPM`. At 30 fps one beat at 120 BPM = 15 frames.
- **Hits are not always beats.** Vocal accents, risers ending, drops. For "edit audio" trends the cut points are the hits, not the metronome.
- librosa can lock to half or double tempo. Sanity check: typical pop 90-130 BPM, trap 130-160 (often felt as half time), EDM 120-128, phonk 130-150. If the detected grid feels wrong in a frame-grab test, halve/double.
- Energy curve finds the drop/chorus: biggest RMS jump after a quiet section.

## 2. Pick the song window

- Short-form: 7-20 s. Start the window **on a downbeat** and end on a downbeat or the end of a phrase (4 or 8 bars).
- Put the strongest visual on the drop. If the drop is at 12 s in the song and you want it 3 s into the reel, the window starts at 9 s.
- Trending sounds on Instagram/TikTok: the in-app sound starts at a fixed point. If the final post will use the in-app sound, align your edit to that start point, and export a version with the reference audio as a guide.
- Fade music in 10-50 ms (avoid click) unless the window starts on a transient, and out over 0.3-1.5 s, or end on a hard hit.

## 3. Build the grid and place events

```python
fps = 30
fr = lambda t: round(t * fps)           # snap every event to the nearest frame
U = beat_period / 2                     # sub-beat unit (8th notes) if the song is busy
```
- **Cuts**: on beats for flow, on hits for impact. Cutting every beat is exhausting; cut every 2 or 4 beats and use every-beat cuts only for bursts (2-4 s) before the drop.
- **Anticipation**: a cut placed 1-2 frames **before** the beat feels tighter on phones (audio latency + perception). Test both and choose consistently.
- **Flashes / shakes / zoom punches**: on hits, 2-6 frames, decaying.
- **Text**: word appears on the vocal syllable or on the beat; hold at least 0.4 s per word for single words, ~0.25 s/word for lines read in rhythm.
- **Change of speed / effect**: on downbeats or drops.
- Keep a table (`timing.json`) of every event with its musical reason; the build script reads it.

## 4. Speed ramps (velocity)

A speed ramp is a time-map `src_t = f(out_t)`. Build it from segments with eased speed:

```python
# speed curve: 1x ... ramps to 4x between hits ... back to 0.3x on the hit
segments = [(out_start, out_end, speed_start, speed_end, ease)]
```
- Ease the speed with smoothstep/cubic in and out; an instant 1x→4x jump looks like a glitch.
- Slow (0.2-0.5x) **on** the hit, fast (2-5x) **between** hits. The hit frame itself shows the key action (impact, turn, look).
- Slow sections need high-fps sources or frame interpolation (`minterpolate`, Resolve Speed Warp, RIFE).
- Add motion blur in fast parts (`tmix=frames=3` or frame-blend in the time-map renderer) to avoid strobing.
- Real case: overhead desk shot, camera-move parts kept at 1x, static parts at 5.6x, every speed change on a strong hit; an optical-flow pass (OpenCV LK + RANSAC similarity) located the camera moves automatically (see `motion-tracking`).

`timemap.py` renders a time-map by pulling the right source frame for every output frame (with optional frame blending) — exact and simpler than chaining setpts filters.

## 5. Matching a reference reel's timing

1. Download/obtain the reference; extract its audio.
2. Detect its cuts: `ffmpeg -i ref.mp4 -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep pts_time`.
3. Detect beats on its audio; express each cut as a beat index or offset → that is the rhythm template.
4. Measure text on/off times by stepping frames (1/30 s precision) around changes.
5. Rebuild with your footage on the same grid (see `reference-matching`).

## 6. Verify

- Scene-detect the render; every cut time × fps should equal its planned frame (±0).
- Overlay a click track on beats in a debug render (`aevalsrc` sine bursts) and grab frames at hits.
- You cannot listen: report the numbers (planned vs measured cut frames), and ask the user to check by ear.
