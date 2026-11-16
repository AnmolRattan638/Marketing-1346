import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_HEAD, LOGO_SAFE_TOP, THEME } from "./theme";
import { fade, pop } from "./anim";

export interface BeforeAfterSpec {
  beforeTitle: string;
  beforeItems: string[];
  afterTitle: string;
  afterItems: string[];
}

// BEFORE (no website, no digital marketing: the struggle) on top, AFTER (website + chatbot) below, built for a portrait phone screen with large text.
// Timing is relative to `at` (the scene's heading time): the before card and its rows first, the after card a moment later. Colours: theme only.
const Row: React.FC<{ text: string; mark: string; color: string; textColor: string; t: number; dx: number }> = ({ text, mark, color, textColor, t, dx }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, t);
  return (
    <div style={{ display: "flex", gap: 22, alignItems: "flex-start", padding: "9px 0", opacity: Math.min(1, p), transform: `translateX(${(1 - Math.min(1, p)) * dx}px)` }}>
      <span style={{ fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 44, lineHeight: "50px", color, width: 44, textAlign: "center" }}>{mark}</span>
      <span style={{ fontFamily: FONT_HEAD, fontWeight: 600, fontSize: 40, lineHeight: "48px", color: textColor }}>{text}</span>
    </div>
  );
};

export const BeforeAfterBoard: React.FC<{ spec: BeforeAfterSpec; at: number }> = ({ spec, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tB = at, tA = at + 0.5 + spec.beforeItems.length * 0.45 + 0.4;
  const pB = pop(frame, fps, tB), pA = pop(frame, fps, tA);
  const arrow = fade(frame, fps, tA - 0.35, 0.3);
  const card = (border: string, bg: string, p: number, dy: number): React.CSSProperties => ({
    width: 920, boxSizing: "border-box", padding: "30px 38px", borderRadius: 34, background: bg, border: `4px solid ${border}`,
    opacity: Math.min(1, p), transform: `translateY(${(1 - Math.min(1, p)) * dy}px)`, boxShadow: `0 20px 60px rgba(0,0,0,0.25)`,
  });
  const title = (c: string): React.CSSProperties => ({ fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 36, letterSpacing: 3, textTransform: "uppercase", color: c, marginBottom: 10 });
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: LOGO_SAFE_TOP + 20 }}>
      <div style={card(THEME.cardEdge, THEME.card, pB, -30)}>
        <div style={title(THEME.muted)}>{spec.beforeTitle}</div>
        {spec.beforeItems.map((x, i) => <Row key={i} text={x} mark={"✗"} color={THEME.muted} textColor={THEME.muted} t={tB + 0.5 + i * 0.45} dx={-30} />)}
      </div>
      <div style={{ fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 64, color: THEME.accent, opacity: arrow, margin: "6px 0", transform: `translateY(${(1 - arrow) * -12}px)` }}>{"↓"}</div>
      <div style={card(THEME.accent, THEME.card, pA, 40)}>
        <div style={title(THEME.accent)}>{spec.afterTitle}</div>
        {spec.afterItems.map((x, i) => <Row key={i} text={x} mark={"✓"} color={THEME.accent} textColor={THEME.text} t={tA + 0.5 + i * 0.45} dx={30} />)}
      </div>
    </AbsoluteFill>
  );
};
