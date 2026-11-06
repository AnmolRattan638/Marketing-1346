import React from "react";
import { Img, staticFile, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export interface KenBurnsTransform {
  scale?: number;
  x?: number; // pixels
  y?: number;
}

export interface KenBurnsProps {
  src: string;
  from?: KenBurnsTransform;
  to?: KenBurnsTransform;
  width?: number | string;
  height?: number | string;
  objectFit?: React.CSSProperties["objectFit"];
}

// Ken Burns pan/zoom over a still image. `from` and `to` are transforms
// interpolated linearly across the parent Sequence duration.
export const KenBurns: React.FC<KenBurnsProps> = ({
  src,
  from = { scale: 1, x: 0, y: 0 },
  to = { scale: 1.15, x: 0, y: 0 },
  width = "100%",
  height = "100%",
  objectFit = "cover",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const scale = interpolate(frame, [0, durationInFrames], [from.scale ?? 1, to.scale ?? 1]);
  const x = interpolate(frame, [0, durationInFrames], [from.x ?? 0, to.x ?? 0]);
  const y = interpolate(frame, [0, durationInFrames], [from.y ?? 0, to.y ?? 0]);

  return (
    <div style={{ width, height, overflow: "hidden" }}>
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit,
          transform: `scale(${scale}) translate(${x}px, ${y}px)`,
          transformOrigin: "center",
        }}
      />
    </div>
  );
};
