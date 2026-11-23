import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionWord, chunkWords } from "./Captions";

export type CaptionStyle = "pill" | "cinematic" | "karaoke" | "stack" | "typewriter" | "chest" | "glass" | "depth" | "smoke" | "wallink" | "orbit" | "bounce" | "neon" | "giant" | "explode" | "retro" | "outline" | "hierarchy" | "goldcta" | "serifface" | "quoted";

export const SANS = '"Montserrat", "Poppins", "Inter", "Noto Sans Devanagari", "Noto Sans", "Helvetica Neue", Arial, sans-serif';
export const MONO = '"JetBrains Mono", "Fira Code", "DejaVu Sans Mono", Menlo, Consolas, monospace';
export const norm = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");

export interface CaptionZone {
  from: number; // seconds from the scene start
  to: number;
  y: number; // centre of the caption area on the 1920 px frame (agent/caption_zones.py)
}
export const DEFAULT_Y = 1400; // where the styles sit by themselves (the bottom area)

export interface Props {
  words: CaptionWord[];
  zones?: CaptionZone[];
  emphasis?: string[];
  style?: CaptionStyle;
  upper?: boolean;
  bottom?: number;
  anchors?: string[]; // serifface: planner placement per phrase, e.g. "top-left", "mid-right", "low-left"
}

// Which phrase is on screen right now, and how far through its life we are. Shared by the styles below.
export function useChunk(words: CaptionWord[], maxWords: number, maxChars: number, lead = 0.05, hold = 0.3) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const chunks = chunkWords(words, Math.min(3, maxWords), maxChars); // never more than 3 words on screen
  let c = -1;
  for (let i = 0; i < chunks.length; i++) if (chunks[i][0].start - lead <= t) c = i;
  if (c < 0) return null;
  const chunk = chunks[c];
  const last = chunk[chunk.length - 1];
  const hideAt = last.end + hold;
  if (t > hideAt && c === chunks.length - 1) return null;
  if (t > hideAt + 0.4) return null;
  const inAt = chunk[0].start - lead;
  const isLast = c === chunks.length - 1;
  const outP = isLast ? interpolate(t, [hideAt - 0.15, hideAt], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  let active = 0;
  for (let i = 0; i < chunk.length; i++) if (chunk[i].start <= t) active = i;
  return { frame, fps, t, c, chunk, chunks, inAt, outP, active, local: frame - Math.round(inAt * fps) };
}

export const Box: React.FC<{ bottom: number; children: React.ReactNode }> = ({ bottom, children }) => (
  <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: bottom }}>{children}</AbsoluteFill>
);


// The word of a phrase that gets the big treatment: a planner emphasis word, a number, else the last word.
export function keywordIndex(chunk: CaptionWord[], emphasis: string[] = []): number {
  const emph = new Set(emphasis.map(norm));
  const i = chunk.findIndex((w) => emph.has(norm(w.text)) || /\d/.test(w.text));
  return i >= 0 ? i : chunk.length - 1;
}
