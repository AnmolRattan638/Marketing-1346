import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { pop } from "../graphics/anim";
import { FONT_HEAD, THEME } from "../graphics/theme";

export interface ProcStep {
  text: string;
  at: number; // seconds from the start of this card
}

// A procedure explained as it is spoken: a card that rises in, then each step lights up on its word (number badge pops, line draws to the next step, earlier steps tick off).
export const ProcedureCard: React.FC<{ title?: string; steps: ProcStep[]; seconds: number }> = ({ title, steps, seconds }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = pop(frame, fps, 0, { damping: 16, stiffness: 150, mass: 0.8 });
  const out = interpolate(frame, [(seconds - 0.35) * fps, seconds * fps], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const t = frame / fps;
  const active = steps.reduce((a, s, i) => (t >= s.at ? i : a), -1);
  const ROW = 118;
  const lineFill = steps.length > 1 ? steps.slice(1).reduce((a, st) => a + Math.min(1, Math.max(0, (t - st.at) / 0.4)), 0) / (steps.length - 1) : 0;
  return (
    <div
      style={{
        width: 920, padding: "34px 40px 30px", borderRadius: 34, background: "rgba(6,8,13,0.95)", border: `2px solid ${THEME.cardEdge}`,
        boxShadow: `0 24px 70px rgba(0,0,0,.55), 0 0 60px ${THEME.glowSoft}`, fontFamily: FONT_HEAD,
        opacity: Math.min(1, enter * 1.4) * out, transform: `translateY(${(1 - Math.min(1, enter)) * 60}px) scale(${0.95 + 0.05 * Math.min(1, enter)})`,
      }}
    >
      {title ? <div style={{ color: THEME.accent, fontSize: 36, fontWeight: 800, letterSpacing: 4, textTransform: "uppercase", marginBottom: 22 }}>{title}</div> : null}
      <div style={{ position: "relative", height: steps.length * ROW }}>
        {steps.length > 1 ? (
          <div style={{ position: "absolute", left: 35, top: 36, width: 4, height: (steps.length - 1) * ROW, background: THEME.cardEdge, borderRadius: 2 }}>
            <div
              style={{
                width: 4, borderRadius: 2, background: THEME.accent, boxShadow: `0 0 14px ${THEME.glow}`,
                height: `${lineFill * 100}%`,
              }}
            />
          </div>
        ) : null}
        {steps.map((s, i) => {
          const p = pop(frame, fps, s.at, { damping: 14, stiffness: 200, mass: 0.7 });
          const done = i < active;
          const now = i === active;
          return (
            <div key={i} style={{ position: "absolute", top: i * ROW, left: 0, right: 0, height: ROW - 14, display: "flex", alignItems: "center", gap: 28, opacity: 0.35 + 0.65 * Math.min(1, p) }}>
              <div
                style={{
                  width: 72, height: 72, borderRadius: 36, flex: "none", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 38, fontWeight: 900,
                  background: done || now ? THEME.accent : THEME.card, color: done || now ? THEME.ink : THEME.muted, border: `3px solid ${done || now ? THEME.accent : THEME.cardEdge}`,
                  boxShadow: now ? `0 0 34px ${THEME.glow}` : "none", transform: `scale(${now ? 0.9 + 0.1 * Math.min(1.15, p) : 1})`,
                }}
              >
                {done ? "✓" : i + 1}
              </div>
              <div style={{ color: now ? THEME.text : done ? THEME.muted : THEME.text, fontSize: 46, fontWeight: 700, lineHeight: 1.15, transform: `translateX(${(1 - Math.min(1, p)) * 40}px)` }}>{s.text}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
