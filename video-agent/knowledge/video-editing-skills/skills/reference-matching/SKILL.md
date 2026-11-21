---
name: reference-matching
description: Recreate the look and rhythm of a reference video ("make it like this reel") - measure its cut times, shot lengths, beat alignment, text timing and positions, fonts, transitions, grade and audio, write a style spec, then rebuild with the user's footage and compare side by side. Use whenever the user supplies a reference video, a trending format, or says "same style as", "like this one", "copy this edit".
---

# Reference matching

Script: `scripts/analyze_reference.py REF.mp4 OUTDIR` — cut list (scene detection), shot-length stats, beat alignment of each cut, per-shot thumbnail strip, average colour stats, loudness. Writes `OUTDIR/reference.json` and `OUTDIR/strip.png`.

## Workflow

1. **Get the file.** If the user gives a link, ask them to download it, or use `yt-dlp` only for content they have rights to analyse. Keep it in `reference/`.
2. **Analyse** with the script, then look at the strip and frames around each cut.
3. **Write a style spec** (`edit/style_spec.md`): 
   - format: resolution, fps, duration, aspect
   - structure: shot list with durations and what each shot shows (wide/close/detail, subject)
   - rhythm: cuts on which beats/hits; average shot length; where the pace changes
   - text: exact words, font family guess (serif/sans/script/hand, weight), size relative to width, colour, position (fraction of frame), timing to 1/30 s, animation in/out
   - transitions: types and durations
   - grade: warm/cool, contrast, saturation, black level, any grain/vignette
   - audio: song (and the start point), SFX, voice
4. **Map the user's footage** onto the spec: best matching shot for each slot (same size/motion/subject). Tell the user which slots have no good match.
5. **Build** with the same timings; reuse the reference audio as a **guide track** so the grid matches.
6. **Compare**: render side-by-side (`hstack`) of reference and result; check text positions and cut frames match.
   ```bash
   ffmpeg -i ref.mp4 -i out.mp4 -filter_complex "[0:v]scale=540:960[a];[1:v]scale=540:960[b];[a][b]hstack" -an compare.mp4
   ```

## Measuring text precisely

- Step frames around a text change: `ffmpeg -ss T-0.2 -i ref.mp4 -t 0.4 -vf fps=30 f_%02d.png`.
- Position: express as fractions of width/height so it scales to 4K.
- Size: measure cap height in px / frame height.
- Font: identify the category and closest free font (e.g. Caveat for hand-lettering, Great Vibes for swash script, Cormorant/Playfair for elegant serif, Cooper Black for retro, Montserrat/Inter for clean sans). Tell the user it's the closest match, not necessarily the exact font.
- Colour: sample text pixels at the centre of strokes (not anti-aliased edges).

## Rules

- Match the feel, never copy someone else's footage, logo or watermark into the output.
- Keep the reference's quote/text only if the user asks for the same words; otherwise adapt.
- Instagram reference audio: the final post should use the in-app sound starting at the same point; export a version with the guide audio for review and one silent version for upload.
- When the user says "match the reference picture", text position and curvature matter as much as font: measure, don't eyeball.
