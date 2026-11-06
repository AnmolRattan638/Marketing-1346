import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { defaultTheme } from "../theme";

export interface ProgressBarProps {
  value: number;           // 0..1
  label?: string;
  durationFrames?: number; // animate from 0 to value over this many frames
  height?: number;
  width?: number | string;
  color?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  label,
  durationFrames = 30,
  height = 12,
  width = 400,
  color,
}) => {
  const frame = useCurrentFrame();
  const t = defaultTheme;
  const fill = color ?? t.colors.accent;

  const animated = interpolate(frame, [0, durationFrames], [0, value], {
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, width }}>
      {label && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 16,
            color: t.colors.fg,
            fontFamily: t.fonts.body,
          }}
        >
          <span>{label}</span>
          <span style={{ color: t.colors.mute }}>{Math.round(animated * 100)}%</span>
        </div>
      )}
      <div
        style={{
          height,
          background: t.colors.mute + "33",
          borderRadius: height / 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${animated * 100}%`,
            background: fill,
            borderRadius: height / 2,
          }}
        />
      </div>
    </div>
  );
};
