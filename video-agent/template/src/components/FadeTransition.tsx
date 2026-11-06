import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export interface FadeTransitionProps {
  children: React.ReactNode;
  durationFrames?: number;
  direction?: "in" | "out" | "both";
}

// Wraps children with a fade. "both" fades in at start and out at end of
// the parent Sequence.
export const FadeTransition: React.FC<FadeTransitionProps> = ({
  children,
  durationFrames = 15,
  direction = "both",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn =
    direction === "out"
      ? 1
      : interpolate(frame, [0, durationFrames], [0, 1], { extrapolateRight: "clamp" });

  const fadeOut =
    direction === "in"
      ? 1
      : interpolate(
          frame,
          [durationInFrames - durationFrames, durationInFrames],
          [1, 0],
          { extrapolateLeft: "clamp" }
        );

  const opacity = Math.min(fadeIn, fadeOut);

  return <div style={{ opacity, width: "100%", height: "100%" }}>{children}</div>;
};
