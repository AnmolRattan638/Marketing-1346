import { interpolate, random } from "remotion";

export type Arrival = "settle" | "whip" | "zoom" | "iris" | "glitch";
export interface Look {
  scale: number;
  translateX: number; // px
  translateY: number; // px
  blur: number; // px
  opacity: number;
  hue: number; // deg
  brightness: number;
  clip?: string; // clip-path
}

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const easeOut = (p: number) => 1 - Math.pow(1 - clamp01(p), 3);

// How a scene ARRIVES, in its first frames. The cut itself is a hard cut (audio, words and captions never move);
// these are the whip-pan, zoom-through, iris and glitch looks of the template pack, rewritten so they only need the incoming
// picture: it is over-scaled so the shifted edges never show black.
export function arrival(kind: Arrival, frame: number, fps: number): Look {
  const base: Look = { scale: 1, translateX: 0, translateY: 0, blur: 0, opacity: 1, hue: 0, brightness: 1 };
  switch (kind) {
    case "whip": {
      // whip-pan: the picture lands from the right at speed: shifted, stretched, motion-blurred, then locked
      const p = clamp01(frame / (fps * 0.3));
      const e = easeOut(p);
      return { ...base, scale: 1.14 + (1 - e) * 0.1, translateX: (1 - e) * 120, blur: (1 - e) * 26 };
    }
    case "zoom": {
      // zoom-through: arrives from close up, focus pulls in
      const p = clamp01(frame / (fps * 0.4));
      const e = easeOut(p);
      return { ...base, scale: 1 + (1 - e) * 0.55, blur: (1 - e) * 18, opacity: 0.45 + 0.55 * clamp01(p * 2.2) };
    }
    case "iris": {
      // iris open: a circle grows from the centre
      const p = clamp01(frame / (fps * 0.45));
      return { ...base, clip: `circle(${interpolate(easeOut(p), [0, 1], [0, 75])}% at 50% 50%)` };
    }
    case "glitch": {
      // glitch flash: jitter, colour shift and a brightness kick that decay over ~0.3 s
      const d = clamp01(1 - frame / (fps * 0.3));
      if (d <= 0) return base;
      return {
        ...base,
        scale: 1.06,
        translateX: (random(`ax${frame}`) - 0.5) * 70 * d,
        translateY: (random(`ay${frame}`) - 0.5) * 24 * d,
        hue: (random(`ah${frame}`) - 0.5) * 120 * d,
        brightness: 1 + 0.5 * d * (random(`ab${frame}`) > 0.5 ? 1 : 0),
      };
    }
    default: {
      // settle: arrives slightly zoomed in and eases back as the whoosh dies
      return { ...base, scale: 1 + 0.05 * Math.exp(-frame / 5) };
    }
  }
}

// Decaying camera shake (camera-shake): several sine frequencies for an organic feel. Several shakes can overlap.
export function shake(frame: number, fps: number, items: { atSecond: number; seconds: number }[]): { x: number; y: number; scale: number } {
  let x = 0;
  let y = 0;
  let active = 0;
  for (const s of items) {
    const f = frame - Math.round(s.atSecond * fps);
    const len = Math.max(1, Math.round(s.seconds * fps));
    if (f < 0 || f > len) continue;
    const amp = 26 * Math.pow(1 - f / len, 1.5);
    x += Math.sin(f * 0.85) * amp + Math.sin(f * 2.3) * amp * 0.3;
    y += Math.cos(f * 1.15) * amp + Math.cos(f * 2.9) * amp * 0.3;
    active = Math.max(active, amp);
  }
  return { x, y, scale: 1 + active / 520 }; // a little over-scale keeps the edges covered while it moves
}
