import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { pop } from "./anim";
import { FONT_HEAD, FONT_SERIF, THEME } from "./theme";

// Kinetic heading: a small kicker line with an underline that draws itself, then the big words rising out of a mask one after another.
// `at` = the spoken word it belongs to.
export const Heading: React.FC<{
  kicker?: string;
  heading: string;
  heading2?: string;
  at: number;
  align?: "left" | "center";
  size?: number;
  accent?: string;
  second?: string;
}> = ({ kicker, heading, heading2, at, align = "left", size = 128, accent = THEME.accent, second = THEME.text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = pop(frame, fps, at, { damping: 18, stiffness: 160, mass: 0.8 });
  const words = (s: string) => s.split(/\s+/).filter(Boolean);
  const row = (text: string, color: string, delay: number, fs: number) => (
    <div style={{ display: "flex", flexWrap: "wrap", gap: `0 ${fs * 0.22}px`, justifyContent: align === "center" ? "center" : "flex-start" }}>
      {words(text).map((w, i) => {
        const p = pop(frame, fps, at + delay + i * 0.09, { damping: 15, stiffness: 210, mass: 0.7 });
        return (
          <span key={i} style={{ display: "inline-block", overflow: "hidden", paddingBottom: fs * 0.12, marginBottom: -fs * 0.12 }}>
            <span
              style={{
                display: "inline-block",
                transform: `translateY(${(1 - p) * 115}%)`,
                fontFamily: FONT_HEAD,
                fontWeight: 900,
                fontSize: fs,
                lineHeight: 1.02,
                letterSpacing: -2,
                color,
                textTransform: "uppercase",
                textShadow: "0 8px 24px rgba(0,0,0,0.35)",
              }}
            >
              {w}
            </span>
          </span>
        );
      })}
    </div>
  );
  return (
    <div style={{ textAlign: align }}>
      {kicker ? (
        <div style={{ marginBottom: 18, opacity: Math.min(1, k * 1.4) }}>
          <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 600, fontSize: 52, color: THEME.muted }}>{kicker}</div>
          <div style={{ height: 5, width: `${interpolate(k, [0, 1], [0, 100])}%`, maxWidth: 260, margin: align === "center" ? "10px auto 0" : "10px 0 0", background: accent, borderRadius: 3 }} />
        </div>
      ) : null}
      {row(heading, accent, 0.05, size)}
      {heading2 ? row(heading2, second, 0.05 + words(heading).length * 0.09, Math.round(size * 0.82)) : null}
    </div>
  );
};

export const StepBadge: React.FC<{ text: string; at: number }> = ({ text, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at, { damping: 12, stiffness: 240, mass: 0.6 });
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 14,
        background: THEME.ink,
        border: `2px solid ${THEME.cardEdge}`,
        color: "#fff",
        borderRadius: 40,
        padding: "12px 30px",
        fontFamily: FONT_HEAD,
        fontWeight: 800,
        fontSize: 38,
        letterSpacing: 2,
        transform: `scale(${0.6 + 0.4 * p})`,
        opacity: Math.min(1, p * 2),
        transformOrigin: "left center",
        boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
      }}
    >
      <span style={{ width: 14, height: 14, borderRadius: 7, background: THEME.accent }} />
      {text}
    </div>
  );
};

export const Chips: React.FC<{ items: string[]; at: number; align?: "left" | "center" }> = ({ items, at, align = "left" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: align === "center" ? "center" : "flex-start" }}>
      {items.map((c, i) => {
        const p = pop(frame, fps, at + i * 0.12, { damping: 12, stiffness: 240, mass: 0.6 });
        return (
          <div
            key={i}
            style={{
              transform: `scale(${0.5 + 0.5 * p}) translateY(${(1 - p) * 20}px)`,
              opacity: Math.min(1, p * 2),
              background: i === 0 ? THEME.accent : THEME.cardEdge,
              color: i === 0 ? THEME.ink : "#fff",
              border: i === 0 ? "none" : `2px solid ${THEME.cardEdge}`,
              borderRadius: 40,
              padding: "14px 32px",
              fontFamily: FONT_HEAD,
              fontWeight: 800,
              fontSize: 36,
              letterSpacing: 1.5,
              textTransform: "uppercase",
            }}
          >
            {c}
          </div>
        );
      })}
    </div>
  );
};
