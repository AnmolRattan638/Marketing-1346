import { interpolate, spring } from "remotion";

type Cfg = { damping?: number; stiffness?: number; mass?: number };
const SOFT: Cfg = { damping: 14, stiffness: 190, mass: 0.7 };

// 0 -> 1 spring that starts at `at` seconds (the moment of the spoken word).
export const pop = (frame: number, fps: number, at: number, config: Cfg = SOFT) =>
  spring({ frame: frame - Math.round(at * fps), fps, config });

export const fade = (frame: number, fps: number, at: number, dur = 0.25) =>
  interpolate(frame, [at * fps, (at + dur) * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

// The text typed so far (characters per second), as in the terminal and comment mock-ups.
export const typed = (text: string, frame: number, fps: number, at: number, cps = 16) =>
  text.slice(0, Math.max(0, Math.min(text.length, Math.floor((frame / fps - at) * cps))));

export const blink = (frame: number, fps: number) => Math.floor(frame / (fps * 0.5)) % 2 === 0;
export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
