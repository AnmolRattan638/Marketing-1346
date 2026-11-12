import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { THEME } from "./theme";

// A thin bar along the bottom that fills across the whole reel (progress = [start, end] of this scene), like the reference's INTRO / STEPS / LINK bar.
export const ProgressBar: React.FC<{ progress: [number, number]; light?: boolean }> = ({ progress, light }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = interpolate(frame, [0, durationInFrames], progress, { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 150 }}>
      <div style={{ width: 640, height: 8, borderRadius: 4, background: "rgba(255,255,255,0.18)", overflow: "hidden" }}>
        <div style={{ width: `${p * 100}%`, height: "100%", borderRadius: 4, background: light ? "#fff" : THEME.accent }} />
      </div>
    </AbsoluteFill>
  );
};
