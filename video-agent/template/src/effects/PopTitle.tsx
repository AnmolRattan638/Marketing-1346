import React from "react";
import { THEME } from "../graphics/theme";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT } from "./fonts";

// Adapted from bounce-text: a gradient card scales in while the text slides in from the left, then both ease out.
export const PopTitle: React.FC<{ text: string; label?: string }> = ({ text, label }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const scale = spring({ frame, fps, from: 0.6, to: 1, config: { damping: 13, stiffness: 200, mass: 0.7 } });
  const slide = spring({ frame, fps, from: -60, to: 0, config: { damping: 18, stiffness: 190, mass: 0.8 } });
  const fade = spring({ frame, fps, from: 0, to: 1, config: { damping: 40, mass: 0.6 } });
  const sub = spring({ frame: frame - 8, fps, from: 0, to: 1, config: { damping: 40, mass: 0.6 } });
  const out = interpolate(frame, [durationInFrames - 7, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 470, opacity: out }}>
      <div
        style={{
          transform: `scale(${scale})`,
          opacity: fade,
          background: `linear-gradient(45deg, ${THEME.accent2}, ${THEME.accent})`,
          borderRadius: 34,
          boxShadow: `0 18px 54px ${THEME.glow}`,
          padding: "30px 54px",
          maxWidth: 920,
          fontFamily: FONT,
          overflow: "hidden",
        }}
      >
        <div style={{ transform: `translateX(${slide}%)` }}>
          <div style={{ fontSize: 86, fontWeight: 900, lineHeight: 1.05, color: THEME.ink, textAlign: "center" }}>{text}</div>
          {label ? (
            <div style={{ marginTop: 10, fontSize: 44, fontWeight: 600, color: THEME.ink, textAlign: "center", opacity: sub }}>{label}</div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
