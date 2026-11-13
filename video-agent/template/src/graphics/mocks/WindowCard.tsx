import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { pop } from "../anim";
import { FONT_HEAD, THEME } from "../theme";

// The card every mock-up sits in: three window dots, an optional title, and a spring-in from below (the reference's UI-window look).
export const WindowCard: React.FC<{
  at: number;
  width?: number;
  height?: number;
  title?: string;
  dark?: boolean;
  children?: React.ReactNode;
}> = ({ at, width = 920, height, title, dark = false, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at, { damping: 15, stiffness: 170, mass: 0.8 });
  return (
    <div
      style={{
        width,
        height,
        transform: `translateY(${(1 - p) * 120}px) scale(${0.92 + 0.08 * p})`,
        opacity: Math.min(1, p * 2.2),
        background: dark ? THEME.ink : THEME.card,
        border: `2px solid ${THEME.cardEdge}`,
        borderRadius: 38,
        boxShadow: "0 30px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04) inset",
        overflow: "hidden",
        fontFamily: FONT_HEAD,
        color: THEME.text,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "24px 30px 0" }}>
        {[THEME.accent2, THEME.accent, THEME.hot].map((c) => (
          <span key={c} style={{ width: 20, height: 20, borderRadius: 10, background: c }} />
        ))}
        {title ? <span style={{ marginLeft: 16, fontSize: 28, fontWeight: 600, color: THEME.muted }}>{title}</span> : null}
      </div>
      <div style={{ padding: "24px 36px 36px" }}>{children}</div>
    </div>
  );
};
