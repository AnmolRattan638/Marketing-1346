---
name: style-explainer
description: Explainer and tutorial editing style - software demos, SaaS launch videos, coding tutorials, screen recordings, how-to videos and educational explainers - script-first structure, voiceover-synced visuals, cursor-focused zooms and pans on screen recordings, callouts, highlights and step numbers, diagrams and animated illustrations, chapter cards, and clear captions. Use for product demos, tutorials, screencasts, launch videos and any "explain how X works" video.
---

# Style: Explainer / Tutorial / Demo

Load with: `style-motion-graphics`, `captions-typography`, `sound-design`, `ffmpeg-pipeline`. Upstream HyperFrames/Remotion are strong for UI animation.

## Signature

- Script first: one idea per scene; visuals land exactly on the words that describe them.
- Screen recordings are never shown full-frame for long: zoom (150-250%) to the area being discussed, pan with eased motion following the cursor.
- Callouts: highlight boxes, arrows, blur/dim everything else (spotlight), step numbers.
- Clean, branded palette; plenty of empty space; 1-2 fonts.
- Pace: simple cards 3-7 s, complex diagrams 8-14 s; final frame held ≥ 1 s.

## Structures

- Launch: Hook (the result) → Problem → Solution (product) → 3 features with demo → Proof → CTA.
- Tutorial: Outcome preview → Setup → Steps (numbered) → Gotchas → Recap.
- Concept explainer: Question → Intuition (analogy) → Mechanism (diagram) → Example → Takeaway.

## Screen recording workflow

1. Record at 2x the delivery resolution if possible (e.g. 4K screen for 1080 output) so zooms stay sharp; hide personal data; large font sizes in the app/IDE (zoom 125-150%).
2. Log cursor positions (or detect them) and clicks.
3. Zoom plan: per step, a target rectangle; animate between rectangles with ease-in-out 400-700 ms; hold while the action happens.
4. Speed up waiting/typing parts 2-8x; cut loading screens.
5. Add click ripples, keystroke overlays for shortcuts, and highlight boxes that draw on.
6. Voiceover synced: visual change lands on the payoff word (start the animation `reveal_duration` before the word).

## Diagrams

- Build in the order of explanation; one new element at a time.
- Isometric/technical illustrations, Manim for maths, simple vector shapes for flows.
- Arrows draw along their path (stroke-dashoffset style), labels after arrows.

## Quality bar

Text in recordings legible at phone size (zoom more if not); cursor never jumps (smooth it); no personal info/API keys visible in any frame; captions don't cover the UI being explained.
