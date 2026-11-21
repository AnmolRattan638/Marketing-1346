---
name: style-motion-graphics
description: Motion graphics editing style - designed animation of shapes, type, icons, logos, UI and data - logo stings, animated titles, lower thirds, transitions, infographics, charts, product UI animation, explainer scenes - using animation principles (easing, anticipation, overshoot, follow-through, stagger), a design system (grid, palette, type scale), and tools like HyperFrames (HTML/GSAP), Remotion (React), After Effects-style keyframing in Python/PIL, Manim, or Fusion. Use when the user asks for motion graphics, animated text, logo animation, intro/outro, infographic or any designed animation.
---

# Style: Motion graphics

Load with: `captions-typography`, `sound-design`, `ffmpeg-pipeline`. Engine skills if installed: HyperFrames (`heygen-com/hyperframes`), Remotion (`remotion-dev/skills`), Three.js skills for 3D.

## Engine choice

| Engine | Best for |
|---|---|
| HyperFrames (HTML/CSS/GSAP → MP4) | kinetic type, UI mockups, overlays with alpha, web-like design, charts |
| Remotion (React) | data-driven/batch videos, existing React design systems |
| PIL/OpenCV frame rendering + ffmpeg | simple overlays, exact pixel control, curved/hand text, compositing on footage |
| Manim | maths, diagrams, equations, graph morphs |
| Three.js / Blender | real 3D, product turntables, holograms |
| DaVinci Fusion / After Effects | when the user's workflow lives there |

## Design system first

Before animating, define and confirm:
- Canvas, fps (30 or 60 for UI), safe zone, grid (e.g. 12-col or 8 px baseline).
- Palette: background, 1 primary, 1 accent, neutrals (≤ 2 accent colours).
- Type scale: display / headline / body / label sizes (e.g. 1.25-1.333 ratio), two families max.
- Motion tokens: durations (fast 150-250 ms, base 300-500 ms, slow 600-900 ms) and easings.

## Animation principles (non-negotiable)

- **Easing**: ease-out (cubic/expo) for entrances, ease-in for exits, ease-in-out for moves. Never linear (except constant rotation/scroll).
- **Anticipation** and **overshoot**: back-out (`c1 = 1.70158`) for playful pops; no overshoot for premium/corporate.
- **Stagger**: 40-80 ms between letters/items; reveal order follows reading order.
- **One focus at a time**: don't animate two unrelated things simultaneously.
- **Follow-through**: secondary elements settle 1-3 frames after the primary.
- **Hold**: give each message reading time (~ 0.3 s per word + 1 s), hold the final frame ≥ 1 s.
- **Motion blur** on fast moves (render at higher fps and blend, or CSS/shader blur).
- **Transitions between scenes** should continue motion (exit direction = next entrance direction) or use a shape/mask wipe.

## Common pieces

| Piece | Recipe |
|---|---|
| Logo sting (2-4 s) | shape builds → logo resolves with overshoot → light sweep → hold; hit SFX on resolve |
| Lower third | line draws (300 ms) → name slides up from mask (stagger 60 ms) → role fades → hold 3-5 s → reverse faster |
| Title card | big word scale 90→100% + opacity, tracking expands slightly, background subtle gradient drift |
| Kinetic headline | per-word masks rising from baseline, key word in accent colour, on beat |
| Counter | number counts with ease-out to the final value, lands on a hit; tabular figures |
| Chart | axes draw, bars grow with stagger (ease-out), labels after bars land |
| UI demo | device frame, cursor with eased paths, click ripples, zoom into the area being discussed |
| Transition | shape wipe (circle/rect) in brand colour, 300-500 ms, on beat |

## Rendering and compositing

- Render overlays with alpha (PNG sequence, ProRes 4444, WebM VP9 alpha) and composite on footage in ffmpeg.
- Assert fonts loaded before rendering in browser engines.
- Deterministic: no `Math.random()` without a seed, no real-time clocks; animation is a pure function of frame number.
- Render at final resolution (vector graphics upscaled from 1080 look soft at 4K).

## Quality bar

Check stills at the start, mid and end of every animation; scrub frames around each transition for pops (elements appearing for 1 frame), misaligned baselines, clipped glyphs, and colour banding in gradients (add 1-2% noise/dither).
