---
name: style-velocity-edit
description: Velocity edit / "edit audio" style - high-energy beat-locked edits for cars, sports, gym, gaming, anime, fashion and travel - speed ramps (fast between hits, slow on hits), zoom punches, camera shake, white flashes, RGB split, motion blur, strobe bursts of stills, whip transitions, and heavy contrast grades. Use when the user wants a velocity edit, phonk edit, AMV/fan edit, hype edit, or "edit like the trend".
---

# Style: Velocity edit

Load with: `beat-sync` (essential), `ffmpeg-pipeline`, `color-grading`, `motion-tracking` (optional), `sound-design`.

## Signature

- Every visual event is on the music: hits drive speed changes, flashes, shakes, cuts.
- Speed ramps: **fast (2-6x) between hits, slow (0.2-0.5x) on the hit**, eased in and out.
- Shot length 0.2-1 s; 1-sub-beat bursts of stills/frames before drops.
- Effects: zoom punch (scale 100→115→100% over 4-6 frames), camera shake (decaying random offset 10-40 px, 6-10 frames), white flash (2-3 frames, 60-100%), RGB split (channel offsets 6-20 px, 3-5 frames), directional motion blur, glow on highlights.
- Grade: high contrast, crushed but not clipped blacks, saturated or monochrome with one accent colour.
- Music: phonk, drift, hard trap, remixed "edit audios" with clear hits.

## Build recipe

1. `beats.py song.mp3 --hit-threshold 0.75` → strong hits only. Pick 8-20 hits for a 10-20 s edit.
2. For each source clip, choose the **key moment** (impact, turn, look, jump). That frame must land exactly on a hit.
3. Write a time-map per clip (`timemap.py`): ramp up to 3-5x after the previous hit, decelerate with ease-out to 0.3x landing on the key frame, hold slow for 4-10 frames, ramp out.
4. Add frame blending in fast parts (`--blend 3`) — strobing looks cheap.
5. Effects layer (Python/OpenCV per frame, or ffmpeg):
   - zoom punch: `scale = 1 + 0.15 * exp(-k * frames_since_hit)`
   - shake: offset = A · noise · exp(-frames_since_hit/3)
   - flash: blend toward white with alpha 0.8 → 0 over 3 frames
   - RGB split: shift R left/B right by `d · exp(-n/2)`
6. Optional: 3-6 still frames at 1-2 frames each (strobe burst) before the drop.
7. Text (if any): one or two words, huge, on hits; glitch in.
8. Render 30 or 60 fps (60 makes fast parts smoother on TikTok/Shorts).

## ffmpeg shortcuts

- Flash on hit at t=H: `eq=brightness='0.6*exp(-(t-H)*25)*gte(t,H)'` (chain or build expression for several hits).
- RGB split: `rgbashift=rh=-8:bh=8` within `enable='between(t,H,H+0.12)'`.
- Shake: `crop=iw-40:ih-40:20+15*sin(t*90)*exp(-(t-H)*8):20+15*cos(t*77)*exp(-(t-H)*8)` then scale back.
- Motion blur: `tmix=frames=3:weights="1 1 1"` on fast segments.

## Quality bar

- Measure: every key frame within ±1 frame of its hit.
- No more than 2-3 effect types stacked on a single hit.
- One calm moment (slow, no effects) before the final drop makes the drop hit harder.
