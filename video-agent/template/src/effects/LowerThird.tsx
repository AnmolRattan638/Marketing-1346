import React from "react";
import { THEME } from "../graphics/theme";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT } from "./fonts";

// Adapted from lower-third: an accent line, then a bar slide in from the left; the text fades in last. Sits clear of the captions
// (they live at the bottom) and of the logo bug (top left).
export const LowerThird: React.FC<{ text: string; label?: string }> = ({ text, label }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const accent = spring({ frame, fps, from: -600, to: 0, durationInFrames: 22, config: { damping: 15, mass: 0.6 } });
  const bar = spring({ frame: Math.max(0, frame - 4), fps, from: -900, to: 0, durationInFrames: 26, config: { damping: 14, mass: 0.7 } });
  const textOpacity = spring({ frame: Math.max(0, frame - 12), fps, from: 0, to: 1, durationInFrames: 18 });
  const out = interpolate(frame, [durationInFrames - 8, durationInFrames], [0, 1], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "flex-start", paddingTop: 520, paddingLeft: 56 }}>
      <div style={{ transform: `translateX(${-out * 900}px)`, fontFamily: FONT }}>
        <div style={{ width: 340, height: 6, borderRadius: 3, background: `linear-gradient(90deg, ${THEME.accent}, ${THEME.accent2})`, transform: `translateX(${accent}px)`, marginBottom: 8 }} />
        <div style={{ display: "flex", transform: `translateX(${bar}px)` }}>
          <div style={{ width: 10, background: THEME.accent, borderRadius: "5px 0 0 5px" }} />
          <div style={{ background: "rgba(6,8,13,0.84)", padding: "22px 46px 24px 36px", borderRadius: "0 12px 12px 0" }}>
            <div style={{ color: THEME.text, fontSize: 64, fontWeight: 900, letterSpacing: 0.5, opacity: textOpacity }}>{text}</div>
            {label ? <div style={{ color: THEME.muted, fontSize: 38, fontWeight: 500, marginTop: 6, opacity: textOpacity }}>{label}</div> : null}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
