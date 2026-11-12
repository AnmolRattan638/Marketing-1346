import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { THEME } from "./theme";

// Arrival "circle": the scene is covered by a colour layer that has a round hole growing from the centre (the reference's circle wipe, incoming half only,
// so audio and captions stay where they are).
export const CircleWipe: React.FC<{ color?: string }> = ({ color = THEME.accent }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const dur = Math.round(fps * 0.5);
  if (frame >= dur) return null;
  const e = 1 - Math.pow(1 - interpolate(frame, [0, dur], [0, 1]), 3);
  const r = e * Math.hypot(width, height) * 0.6;
  return (
    <AbsoluteFill
      style={{
        background: color,
        WebkitMaskImage: `radial-gradient(circle at 50% 50%, transparent ${r}px, #000 ${r + 2}px)`,
        maskImage: `radial-gradient(circle at 50% 50%, transparent ${r}px, #000 ${r + 2}px)`,
      }}
    />
  );
};
