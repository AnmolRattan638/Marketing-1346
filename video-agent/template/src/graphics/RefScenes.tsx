// Scene layouts, overlays and arrivals from the two reference reels. Brand palette only (the references' forest-green and cream become navy and ice-white).
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fade, pop } from "./anim";
import { FONT_HEAD, FONT_SERIF, LOGO_SAFE_TOP, THEME } from "./theme";

const SERIF_BOLD = '"Cormorant Garamond", "Playfair Display", "Noto Serif", Georgia, serif';
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// Words that fade in one by one (pale to full) on their spoken time, the last one italic: the reference's card text.
const Words: React.FC<{ text: string; at: number; size: number; color: string; italicLast?: boolean; every?: number }> = ({ text, at, size, color, italicLast = true, every = 0.22 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ws = text.split(/\s+/).filter(Boolean);
  return (
    <div style={{ fontFamily: SERIF_BOLD, fontWeight: 700, fontSize: size, lineHeight: 1.12, textAlign: "center", color }}>
      {ws.map((w, i) => {
        const last = italicLast && i === ws.length - 1 && ws.length > 1;
        return <span key={i} style={{ display: "inline-block", margin: "0 0.14em", opacity: 0.3 + 0.7 * fade(frame, fps, at + i * every, 0.3), fontFamily: last ? FONT_SERIF : undefined, fontStyle: last ? "italic" : undefined, fontSize: last ? size * 1.18 : size }}>{w}</span>;
      })}
    </div>
  );
};

// b_numeral_card: a full card with a huge italic serif numeral whose lower half dissolves into the card, the item title built word by word beneath, a smaller line under it.
export const NumeralCard: React.FC<{ numeral: string; title: string; line?: string; at: number }> = ({ numeral, title, line, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, Math.max(0, at - 0.3), { damping: 16, stiffness: 150, mass: 0.8 });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 30%, ${THEME.card}, ${THEME.bgTop})`, justifyContent: "center", alignItems: "center", paddingBottom: 200 }}>
      <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 600, fontSize: 520, lineHeight: 0.9, letterSpacing: -10, color: THEME.hot, opacity: Math.min(1, p * 1.6), transform: `scale(${0.94 + 0.06 * p})`, WebkitMaskImage: "linear-gradient(to bottom, #000 40%, transparent 95%)", maskImage: "linear-gradient(to bottom, #000 40%, transparent 95%)" }}>{numeral}</div>
      <div style={{ marginTop: -40, padding: "0 80px", maxWidth: 960 }}>
        <Words text={title} at={at} size={92} color={THEME.text} italicLast={false} />
        {line ? <div style={{ marginTop: 26, fontFamily: SERIF_BOLD, fontWeight: 600, fontSize: 48, textAlign: "center", color: THEME.muted, opacity: fade(frame, fps, at + 0.5, 0.4) }}>{line}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

// b_cream_card_inverse: the inverse card (ice-white with navy text), words fading in one at a time, the last word bold italic.
export const InverseCard: React.FC<{ text: string; at: number }> = ({ text, at }) => (
  <AbsoluteFill style={{ background: THEME.text, justifyContent: "center", alignItems: "center", padding: "0 90px", paddingBottom: 200 }}>
    <Words text={text} at={at} size={104} color={THEME.bgBottom} />
  </AbsoluteFill>
);

// b_hook_title: the title from frame 0, then number tiles pop around it, each joined to the title by a hairline, in step with the count.
export const HookTiles: React.FC<{ title: string; sub?: string; tiles: string[]; times: number[] }> = ({ title, sub, tiles, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = tiles.length;
  const pos = (i: number) => {                                                           // tiles on an arc around the title
    const a = Math.PI * (1.12 + (0.76 * i) / Math.max(1, n - 1));
    return { x: 540 + 400 * Math.cos(a), y: 880 + 360 * Math.sin(a) * (i % 2 ? 0.8 : 1.15) };
  };
  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        {tiles.map((_, i) => {
          const p = Math.min(1, pop(frame, fps, times[i] ?? 0.7 + i * 0.3));
          const { x, y } = pos(i);
          return <line key={i} x1={540} y1={960} x2={540 + (x - 540) * p} y2={960 + (y - 960) * p} stroke={THEME.text} strokeOpacity={0.7} strokeWidth={2} />;
        })}
      </svg>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: 80 }}>
        <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 700, fontSize: 130, lineHeight: 1, color: THEME.hot, textAlign: "center", textShadow: "0 6px 24px rgba(0,0,0,.6)", maxWidth: 900 }}>{title}</div>
        {sub ? <div style={{ marginTop: 18, fontFamily: SERIF_BOLD, fontWeight: 700, fontSize: 50, color: THEME.text }}>{sub}</div> : null}
      </AbsoluteFill>
      {tiles.map((t, i) => {
        const p = pop(frame, fps, times[i] ?? 0.7 + i * 0.3, { damping: 12, stiffness: 260, mass: 0.5 });
        const { x, y } = pos(i);
        return (
          <div key={i} style={{ position: "absolute", left: x - 62, top: y - 62, width: 124, height: 124, borderRadius: 18, background: THEME.card, border: `2px solid ${THEME.accent2}`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT_SERIF, fontStyle: "italic", fontSize: 76, color: THEME.hot, transform: `scale(${0.6 + 0.4 * p})`, opacity: Math.min(1, p * 2.5), boxShadow: "0 14px 30px rgba(0,0,0,.45)" }}>{t}</div>
        );
      })}
    </AbsoluteFill>
  );
};

// Arrivals "sweep" (blur-through colour sweep: the picture lands out of a heavy blur while the colour passes navy, gold, then clears) and "leak" (a warm light-leak flash).
export const ArrivalOverlay: React.FC<{ kind: "sweep" | "leak" }> = ({ kind }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.round(fps * (kind === "sweep" ? 0.35 : 0.45));
  if (frame >= dur) return null;
  const p = frame / dur;
  if (kind === "sweep") {
    const stops = interpolate(p, [0, 0.45, 1], [0, 1, 0], clamp);
    return (
      <AbsoluteFill style={{ backdropFilter: `blur(${(1 - p) * 38}px)`, background: `linear-gradient(180deg, rgba(201,168,76,${0.55 * stops}), rgba(10,18,32,${0.7 * (1 - p)}))` }} />
    );
  }
  const a = interpolate(p, [0, 0.35, 1], [0, 0.8, 0], clamp);
  return <AbsoluteFill style={{ mixBlendMode: "screen", opacity: a, background: `radial-gradient(90% 70% at 30% 20%, ${THEME.hot}, ${THEME.accent2} 50%, transparent 85%)` }} />;
};

export const REF_ARRIVALS = ["sweep", "leak"];
export { FONT_HEAD, LOGO_SAFE_TOP };
