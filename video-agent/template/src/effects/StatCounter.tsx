import React from "react";
import { THEME } from "../graphics/theme";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT } from "./fonts";

export interface StatCounterProps {
  value: number;
  prefix?: string;
  suffix?: string;
  label?: string;
}

// Adapted from stat-counter: a card springs in, the number counts up, the label fades in under it.
export const StatCounter: React.FC<StatCounterProps> = ({ value, prefix = "", suffix = "", label }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 140, mass: 0.7 } });
  const countEnd = Math.max(12, Math.round(durationInFrames * 0.55));
  const progress = interpolate(frame, [4, countEnd], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const eased = 1 - Math.pow(1 - progress, 3);
  const shown = Number.isInteger(value) ? Math.round(value * eased) : Math.round(value * eased * 10) / 10;
  const labelOpacity = interpolate(frame, [Math.round(countEnd * 0.6), countEnd], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const out = interpolate(frame, [durationInFrames - 7, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 430, opacity: out }}>
      <div
        style={{
          transform: `scale(${0.6 + 0.4 * pop})`,
          opacity: Math.min(1, pop * 1.6),
          background: "rgba(6, 8, 13, 0.78)",
          border: `2px solid ${THEME.accent2}`,
          borderRadius: 36,
          boxShadow: `0 18px 60px rgba(0,0,0,0.5), 0 0 60px ${THEME.glowSoft}`,
          padding: "34px 58px 38px",
          textAlign: "center",
          maxWidth: 900,
          fontFamily: FONT,
        }}
      >
        <div
          style={{
            fontSize: 200,
            fontWeight: 900,
            lineHeight: 1,
            color: THEME.text,
            letterSpacing: -4,
            textShadow: "0 8px 24px rgba(0,0,0,0.45)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          <span style={{ color: THEME.accent }}>{prefix}</span>
          {shown.toLocaleString("en-US")}
          <span style={{ color: THEME.accent }}>{suffix}</span>
        </div>
        {label ? (
          <div
            style={{
              marginTop: 14,
              fontSize: 50,
              fontWeight: 700,
              color: THEME.text,
              letterSpacing: 1,
              opacity: labelOpacity,
              transform: `translateY(${(1 - labelOpacity) * 14}px)`,
            }}
          >
            {label}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
