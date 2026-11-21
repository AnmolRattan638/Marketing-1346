---
name: style-cinematic
description: Cinematic editing style - film-like pacing and look for travel films, brand films, short films, cinematic reels and B-roll sequences - 24 fps motion, 2.39:1 or 1.85:1 framing (or full 9:16 film look), J and L cuts, match cuts, sound-led transitions, motivated camera moves, filmic color grade (teal-orange, Kodak print emulation), halation, grain, letterbox, slow reveals and restraint. Use when the user asks for cinematic, filmic, movie-like, or "make it look like a film".
---

# Style: Cinematic

Load with: `editing-foundations`, `color-grading`, `sound-design`, `ffmpeg-pipeline` (+ `beat-sync` for music-led pieces).

## Signature

- **Motion**: 24 fps with 180° shutter blur. Slow-mo from 48/60 fps conformed to 24. Avoid 30 fps footage looking "video"; it can be conformed to 24 only if speed change is acceptable.
- **Framing**: 2.39:1 letterbox for widescreen (bars must be true black and identical on every shot), or full-bleed vertical with strong composition for reels. Rule of thirds, leading lines, depth (foreground element).
- **Pacing**: 3-8 s shots, held long enough to feel; let shots breathe after big moments. Faster cutting only at the climax.
- **Cuts**: J/L cuts with ambience leading into scenes; match cuts (shape, motion, colour); cut on movement; few or no flashy transitions. Dissolves for time passing; dip to black between chapters.
- **Sound**: designed ambience (wind, city, room), foley details, score that swells; silence before a reveal. Sound often carries the transition (J-cut of the next location's ambience).
- **Grade**: controlled contrast, rolled-off highlights, colour separation (warm skin vs cool backgrounds), slight desaturation; optional film emulation, halation on highlights, grain 3-6%.
- **Text**: minimal; elegant serif or wide-tracked sans titles, small, centred or lower-left; fade in 0.5-1 s.

## Build recipe

1. Choose structure (arrival → exploration → peak → reflection, or three-act).
2. Pick the score; find natural sections (intro, build, peak, outro) with `beats.py` energy curve.
3. Assemble wide establishing → medium → details; reveal the hero shot late.
4. Lay ambience bed per location; add J-cuts (0.5-1.5 s audio lead).
5. Speed: slow-mo (40-50%) for hero moments only.
6. Grade: correction pass → look (`teal-orange` or `film-kodak` at 60-80%) → grain → optional halation.
7. Letterbox (if widescreen): `pad` or draw boxes: for 1920x1080 at 2.39:1 the image height is 803 px → bars ~138 px top/bottom: `drawbox=y=0:h=138:color=black:t=fill,drawbox=y=ih-138:h=138:color=black:t=fill`.
8. Titles: `Cormorant Garamond`/`Playfair Display` or wide-tracked `Montserrat Light`, 1-1.5 s fades.
9. Master to -14 LUFS (web) or -16 to -18 with more dynamics for YouTube films.

## Camera-move vocabulary to cut together

Push-in (intimacy), pull-out (reveal/ending), pan/tilt reveal, parallax (foreground slides past), orbit, top-down, tracking with subject. Cut from a move to a move in the same direction, or from a move to a still at the end of the move.

## Cinematic vertical reels

Same principles at 9:16: slower pace than typical reels (1.5-3 s shots), filmic grade, small elegant text, ambience + score, no meme captions. A thin letterbox inside 9:16 (e.g. 1080x1350 image area) can signal "film".

## Don'ts

- No zoom-blur or glitch transitions, no bouncing text, no stock "cinematic" LUT at 100% without correction.
- Don't over-teal skin. Don't crush every black.
- Don't letterbox and then put captions over the bars inconsistently.
