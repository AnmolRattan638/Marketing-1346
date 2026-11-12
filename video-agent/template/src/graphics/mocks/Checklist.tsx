import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { pop } from "../anim";
import { FONT_HEAD, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// Checklist: every row is visible from the start; each tick draws itself on its spoken word and the row lights up.
export const Checklist: React.FC<{ at: number; title?: string; items: string[]; times: number[] }> = ({ at, title, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <WindowCard at={at} title={title} height={Math.min(760, 200 + items.length * 120)}>
      <div style={{ display: "flex", flexDirection: "column", gap: 26, fontFamily: FONT_HEAD }}>
        {items.map((s, i) => {
          const ta = times[i] ?? at + 0.6 + i * 0.7;
          const row = pop(frame, fps, at + 0.15 + i * 0.1, { damping: 16, stiffness: 190, mass: 0.7 });
          const tick = pop(frame, fps, ta, { damping: 10, stiffness: 300, mass: 0.5 });
          const done = frame / fps >= ta;
          const dash = interpolate(tick, [0, 1], [60, 0], { extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 28, opacity: Math.min(1, row * 2), transform: `translateX(${(1 - row) * -60}px)`, padding: "14px 22px", borderRadius: 26, background: done ? "rgba(53,208,127,0.14)" : "rgba(255,255,255,0.05)", border: `2px solid ${done ? "rgba(53,208,127,0.5)" : THEME.cardEdge}` }}>
              <div style={{ width: 62, height: 62, borderRadius: 31, background: done ? THEME.ok : "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${done ? 0.85 + 0.15 * tick : 1})` }}>
                <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke={THEME.ink} strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: done ? 1 : 0 }}>
                  <path d="M4 12.5l5 5L20 6.5" strokeDasharray="60" strokeDashoffset={dash} />
                </svg>
              </div>
              <div style={{ fontSize: 50, fontWeight: 800, color: done ? "#fff" : THEME.muted }}>{s}</div>
            </div>
          );
        })}
      </div>
    </WindowCard>
  );
};
