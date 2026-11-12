# Third-party notice

The animation styles in this folder are adapted from the free "Remotion Templates by RVE" pack
(https://github.com/reactvideoeditor/remotion-templates, MIT license, by the team at https://www.reactvideoeditor.com).

The originals are 16:9 demo components with fixed content. These versions keep the animation technique and are
rewritten to take their content as props, to fit 1080x1920, to run inside a Remotion `<Sequence>` anchored to a spoken word,
and to be deterministic (no CSS keyframes, no `next/image`, no `Math.random`).

| Here | Adapted from |
|------|--------------|
| `StatCounter.tsx` | `stat-counter.tsx` |
| `GlitchText.tsx` | `glitch-text.tsx` (and the RGB split of `logo-glitch-reveal.tsx`) |
| `PopTitle.tsx` | `bounce-text.tsx` |
| `LowerThird.tsx` | `lower-third.tsx` |
| `motion.ts` shake | `camera-shake.tsx` |
| `motion.ts` whip / zoom / iris / glitch arrivals | `whip-pan.tsx`, `zoom-through.tsx`, `iris-transition.tsx`, `glitch-text.tsx` |
| `FilmGrain.tsx` | `noise-grain.tsx` |

MIT License: permission is granted to use, copy, modify and distribute these templates, provided the copyright and permission notice
of the original is kept.
