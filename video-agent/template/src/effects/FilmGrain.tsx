import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

// Adapted from noise-grain. The original draws 30,000 <rect>s per frame at 1080x1920; one SVG turbulence filter does the same job
// (new seed every other frame, like real film) and renders far faster. Off by default (config.json fx.grain = 0).
export const FilmGrain: React.FC<{ opacity?: number }> = ({ opacity = 0.06 }) => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2) % 24;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "overlay", opacity: Math.min(0.3, Math.max(0, opacity * 4)) }}>
      <svg width="100%" height="100%" preserveAspectRatio="none">
        <filter id="grain" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={seed} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </AbsoluteFill>
  );
};
