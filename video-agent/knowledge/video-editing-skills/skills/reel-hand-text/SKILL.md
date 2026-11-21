---
name: reel-hand-text
description: Put a hand-lettered quote stack on a vertical reel (Instagram/TikTok/Shorts), in the trending style of stacked hand-drawn capitals with mixed word sizes, each line bent along its own curve, soft cream colour blended into the footage. Use when the user wants on-screen text "like this reel", a quote overlay, aesthetic hand-written text, or says "text on the screen like the reference". Renders a 4K transparent PNG with handtext.py and burns it in with ffmpeg without lowering quality.
---

# Reel hand-lettered text

Look being matched: a centred block of hand-drawn capitals over the footage.
- One sentence split into 5-8 short lines, 2-4 words per line.
- Key words big (BELIEVE, DEEPLY, REALITY, CHOICE), filler words small (AND, MY, IN, HAS, BUT, TO).
- Lines are not straight: slight slope, and the lower lines arc into a "smile" (ends higher than middle).
- Every letter is slightly different in size, tilt and baseline, so it reads hand-written.
- Colour soft cream `#FFF2A8` at ~96% opacity with a faint blurred shadow. Bright enough to catch the eye, soft enough to blend with the footage. No outline, no box.
- Text block sits in the upper-middle (starts ~15% from top, ends ~55%), inside the Instagram safe zone. Keep it clear of the bottom 20% (caption/UI) and the right edge (buttons).
- Static for the whole reel (the reference does not animate it).

## Steps

1. Get the quote. Split into lines; give each word a size in px for a 2160-wide canvas: small words 120-170, normal 200-230, hero words 245-260. Widest line should be under ~80% of width.
2. Copy `example_layout.json` (same folder as this file) next to the project, edit `lines`:
   - `slope` deg, + means the right end is lower. Use -5..+4.
   - `arc` px, + means ends higher than middle. Use 0-25 for top lines, 70-110 for the last two lines.
   - Other keys (`color`, `opacity`, `shadow`, `word_gap`, `line_gap`, `jitter`, `seed`, `top`, `width`, `height`, `font`) are documented at the top of `handtext.py`.
3. Render and preview on a real frame:
   ```
   ffmpeg -ss 5 -i SOURCE -frames:v 1 frame.png
   python handtext.py layout.json text_overlay.png --preview frame.png preview.png
   ```
   Look at the preview. Check: no line touching the edges, words do not collide, readable over the brightest frame. If text sits on very bright areas, raise `shadow` to 0.5 before changing colour.
4. Burn in. Overlay the PNG at 0:0 on the full-resolution footage in the same encode as the cut, so the video is encoded once:
   ```
   ffmpeg -i SOURCE -i text_overlay.png -filter_complex "[0:v][1:v]overlay=0:0:format=auto" -c:v libx265 -crf 14 -preset slow -tag:v hvc1 out.mp4
   ```
   Don't use `-loop 1` on the PNG; overlay repeats the last frame by itself, and looping 4K RGBA frames can run out of RAM.
5. Instagram upload copy: H.264 High, 2160x3840, 30fps, CRF 15 with `-maxrate 60M -bufsize 120M`, AAC 320k 48kHz, `-movflags +faststart`.

## Notes

- Font: Caveat Bold (free, OFL: https://fonts.google.com/specimen/Caveat) with `deslant` 0.34 makes upright brush capitals. `handtext.py` looks for `fonts/Caveat-Bold.ttf` next to the layout, then system font folders; set `"font"` in the layout to use another file. If a font already stands upright, set `deslant` to 0.
- Canvas size other than 4K: set `width`/`height` and scale every word size by `width / 2160`.
- `seed` fixes the hand-written jitter so re-renders match exactly; change it for a different "handwriting".
- Worked use: a 16 s overhead-desk motivational reel at 2160x3840 — beat-synced speed ramp underneath, this quote stack static on top for the whole reel, burned in during the single final encode.
- Commands use `python <skill_dir>/handtext.py` where `<skill_dir>` is this skill's folder.
