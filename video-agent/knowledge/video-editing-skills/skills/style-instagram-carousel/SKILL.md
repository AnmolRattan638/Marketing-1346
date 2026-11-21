---
name: style-instagram-carousel
description: Instagram carousel and photo-dump editing style - multi-slide 4:5 posts mixing graded photos and short video clips - "week in frames", photo dumps, educational/swipe carousels, before-after, product series - consistent grade/LUT across every slide, cover slide hook, text hierarchy and swipe cues, portrait videos placed full-frame over a blurred copy, subtle bokeh/bloom finishing, and exports for Canva or direct upload. Use when the user wants an Instagram carousel, photo dump, swipe post, or batch-graded stills and clips.
---

# Style: Instagram carousel / photo dump

Load with: `color-grading`, `captions-typography`, `ffmpeg-pipeline`.

## Specs

- 1080x1350 (4:5) — maximum feed height; all slides same ratio (the first slide sets it).
- Up to 20 slides; video slides up to 60 s each; mix of photos and videos allowed.
- Export photos as high-quality JPEG (quality 90-95, sRGB); videos H.264 1080x1350, 30 fps.
- The grid preview crops to 3:4 centre; keep cover text in the centre.

## Signature

- One consistent look across all slides (same LUT/grade, same grain).
- Slide 1 = hook: the best image + a short title ("week in frames — ep 05").
- Text style consistent: e.g. calm lowercase captions with a serif italic accent in peach; or bold educational headings with numbered slides.
- Portrait/landscape mismatches: place the full frame over a blurred, darkened copy of itself rather than cropping important content.
- Optional finishing: soft highlight bloom, a few drifting out-of-focus orbs (festive), kept away from faces and text.

## Recipe (batch)

1. Collect stills and clips; probe them (HEIC needs conversion: `ffmpeg -i in.heic out.png` or pillow-heif).
2. Choose the look on a comparison grid (`grade.py --compare`); lift very dark sources before the LUT.
3. Batch-grade every still and clip with the same chain; fit to 1080x1350 (cover crop or blurred-background fit).
4. Make the cover slide (title + episode number), optional end slide (CTA / "save this").
5. Educational carousels: 1 idea per slide, headline ≤ 8 words, body ≤ 30 words, slide numbers, arrow/swipe cue on slide 1.
6. Deliver numbered files (`01_cover.jpg`, `02.jpg`, `03.mp4` …) and the caption text.

## Lesson from real posts

Aesthetic "week in frames" carousels tend to get saves but few shares; carousels with a useful takeaway or a story get shared. Suggest adding a story or a takeaway when growth is the goal.
