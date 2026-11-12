import React from "react";
import { AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT } from "./fonts";

// Adapted from glitch-text / logo-glitch-reveal: cyan and magenta copies split off the white title with a jitter that decays to clean.
// The jitter is seeded by the frame, so every render is identical.
export const GlitchText: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const decay = Math.max(0, 1 - frame / (fps * 0.7));
  const jx = (random(`gx${frame}`) - 0.5) * 2 * 26 * decay;
  const jy = (random(`gy${frame}`) - 0.5) * 2 * 10 * decay;
  const split = 4 + 20 * decay;
  const slice = decay > 0.15 && random(`sl${frame}`) > 0.55 ? (random(`sx${frame}`) - 0.5) * 70 : 0;
  const pop = spring({ frame, fps, config: { damping: 10, stiffness: 260, mass: 0.5 } });
  const out = interpolate(frame, [durationInFrames - 6, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  const base: React.CSSProperties = {
    fontFamily: FONT,
    fontWeight: 900,
    fontSize: 132,
    lineHeight: 1.05,
    textAlign: "center",
    textTransform: "uppercase",
    letterSpacing: 2,
    maxWidth: 940,
    gridArea: "1 / 1",
  };

  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 470, opacity: out }}>
      <div style={{ display: "grid", transform: `translate(${jx + slice}px, ${jy}px) scale(${0.8 + 0.2 * pop})` }}>
        <div style={{ ...base, color: "#00F0FF", transform: `translate(${-split}px, ${split / 3}px)`, mixBlendMode: "screen", opacity: 0.9 }}>{text}</div>
        <div style={{ ...base, color: "#FF2BD6", transform: `translate(${split}px, ${-split / 3}px)`, mixBlendMode: "screen", opacity: 0.9 }}>{text}</div>
        <div style={{ ...base, color: "#fff", WebkitTextStroke: "8px #000", paintOrder: "stroke fill", textShadow: "0 8px 26px rgba(0,0,0,0.6)" }}>{text}</div>
      </div>
    </AbsoluteFill>
  );
};
