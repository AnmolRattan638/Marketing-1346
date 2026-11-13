import React from "react";
import { THEME } from "../graphics/theme";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface CaptionWord {
  text: string;
  start: number; // seconds from the start of the scene
  end: number;
}

export interface CaptionsProps {
  words: CaptionWord[];
  emphasis?: string[]; // words the planner marked (same ones that get a pop/riser): coloured, bigger pop
  accent?: string; // pill behind the word being spoken
  emphasisFrom?: string; // gradient for emphasised words
  emphasisTo?: string;
  maxWords?: number; // per phrase
  maxChars?: number; // per phrase, keeps a phrase on at most two lines
  upper?: boolean; // UPPERCASE for Latin scripts (no effect on Devanagari)
  bottom?: number; // distance from the bottom edge in px; keep clear of the app's own buttons
}

const FONT =
  '"Montserrat", "Poppins", "Inter", "Noto Sans Devanagari", "Noto Sans", "Helvetica Neue", Arial, sans-serif';
const LEAD = 0.05; // a phrase appears this early (seconds): the eye needs a moment before the voice gets there
const HOLD = 0.3; // and stays this long after its last word if nothing follows
const PAUSE = 0.35; // a silence this long between words starts a new phrase
const norm = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");

// Split the word stream into short phrases: new phrase after punctuation, a pause, or when the line gets long.
export function chunkWords(words: CaptionWord[], maxWords = 4, maxChars = 24): CaptionWord[][] {
  const out: CaptionWord[][] = [];
  let cur: CaptionWord[] = [];
  let chars = 0;
  for (const w of words) {
    const prev = cur[cur.length - 1];
    const breaks =
      prev &&
      (/[.!?,;:—–।]$/.test(prev.text) ||
        w.start - prev.end > PAUSE ||
        cur.length >= maxWords ||
        chars + w.text.length + 1 > maxChars);
    if (breaks) {
      out.push(cur);
      cur = [];
      chars = 0;
    }
    cur.push(w);
    chars += w.text.length + 1;
  }
  if (cur.length) out.push(cur);
  return out;
}

// Animated phrase captions: each phrase springs in, the word being spoken sits on a coloured pill that pops on its
// first sound, emphasised words get a hotter pill and a bigger pop, and the phrase eases out. Timings are Whisper's.
export const Captions: React.FC<CaptionsProps> = ({
  words,
  emphasis = [],
  accent = THEME.accent,
  emphasisFrom = THEME.accent2,
  emphasisTo = THEME.hot,
  maxWords = 4,
  maxChars = 24,
  upper = true,
  bottom = 400,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (words.length === 0) return null;

  const t = frame / fps;
  const chunks = chunkWords(words, maxWords, maxChars);
  let c = -1;
  for (let i = 0; i < chunks.length; i++) {
    if (chunks[i][0].start - LEAD <= t) c = i;
  }
  if (c < 0) return null;
  const chunk = chunks[c];
  const last = chunk[chunk.length - 1];
  const hideAt = last.end + HOLD;
  if (t > hideAt) return null;

  const inFrame = Math.round((chunk[0].start - LEAD) * fps);
  const local = frame - inFrame;
  const enter = spring({ frame: local, fps, config: { damping: 12, stiffness: 240, mass: 0.6 } });
  const exit = c === chunks.length - 1 ? interpolate(t, [hideAt - 0.12, hideAt], [1, 0], { extrapolateLeft: "clamp" }) : 1;
  const opacity = Math.min(interpolate(local, [0, 3], [0, 1], { extrapolateRight: "clamp" }), exit);

  let active = 0;
  for (let i = 0; i < chunk.length; i++) {
    if (chunk[i].start <= t) active = i;
  }
  const emph = new Set(emphasis.map(norm));
  const chars = chunk.reduce((n, w) => n + w.text.length + 1, 0);
  const fontSize = Math.max(60, Math.min(96, 118 - chars * 1.9));

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: bottom }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: "14px 20px",
          maxWidth: 940,
          fontFamily: FONT,
          fontWeight: 900,
          fontSize,
          lineHeight: 1.1,
          textAlign: "center",
          textTransform: upper ? "uppercase" : "none",
          letterSpacing: upper ? 1 : 0,
          opacity,
          transform: `translateY(${(1 - enter) * 34}px) scale(${0.74 + 0.26 * enter})`,
          transformOrigin: "50% 100%",
        }}
      >
        {chunk.map((w, i) => {
          const isActive = i === active && t >= w.start - 0.01;
          const isEmph = emph.has(norm(w.text)) || /\d/.test(w.text);
          const pop = spring({
            frame: frame - Math.round(w.start * fps),
            fps,
            config: { damping: isEmph ? 7 : 10, stiffness: 320, mass: 0.5 },
          });
          const amp = isEmph ? 0.2 : 0.11;
          const scale = isActive ? 1 + amp * Math.min(1.3, pop) : 1;
          const tilt = isActive ? -2.5 * Math.min(1, pop) : 0;
          return (
            <span
              key={`${c}-${i}`}
              style={{
                display: "inline-block",
                padding: "2px 18px 6px",
                borderRadius: 22,
                transform: `scale(${scale}) rotate(${tilt}deg)`,
                color: isActive ? THEME.ink : isEmph ? accent : THEME.text,
                background: isActive
                  ? isEmph
                    ? `linear-gradient(135deg, ${emphasisFrom}, ${emphasisTo})`
                    : accent
                  : "transparent",
                boxShadow: isActive
                  ? `0 10px 34px ${THEME.glow}`
                  : "none",
                WebkitTextStroke: isActive ? "0px" : `9px ${THEME.ink}`,
                paintOrder: "stroke fill",
                textShadow: isActive ? "none" : "0 6px 18px rgba(0,0,0,0.65)",
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
