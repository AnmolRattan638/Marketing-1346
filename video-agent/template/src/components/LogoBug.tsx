import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { ManifestLogo } from "../types";

// Your logo as a small bug on every frame. Default: top-left, below the phone status bar and clear of the Reels buttons (right and bottom).
export const LogoBug: React.FC<{ logo: ManifestLogo }> = ({ logo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const size = logo.size ?? 120;
  const mx = logo.marginX ?? 48;
  const my = logo.marginY ?? 150;
  const pos = logo.position ?? "top-left";
  const fade = interpolate(frame, [0, fps * 0.5], [0, 1], { extrapolateRight: "clamp" });
  const style: React.CSSProperties = {
    position: "absolute",
    width: size,
    height: size,
    opacity: (logo.opacity ?? 0.92) * fade,
    ...(pos.includes("top") ? { top: my } : { bottom: my }),
    ...(pos.includes("left") ? { left: mx } : { right: mx }),
  };
  return <Img src={staticFile(logo.src)} style={style} />;
};
