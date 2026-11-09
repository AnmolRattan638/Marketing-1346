import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { useFrameSpring } from "../hooks/useFrameSpring";
import { defaultTheme } from "../theme";

export interface StatRevealProps {
  value: number;
  suffix?: string;
  prefix?: string;
  durationFrames?: number;
  easing?: "spring" | "linear";
  fontSize?: number;
  label?: string;
}

// Animated counter. Counts up from 0 to `value` over `durationFrames`.
export const StatReveal: React.FC<StatRevealProps> = ({
  value,
  suffix = "",
  prefix = "",
  durationFrames = 30,
  easing = "spring",
  fontSize = 120,
  label,
}) => {
  const frame = useCurrentFrame();
  const t = defaultTheme;

  const progressSpring = useFrameSpring({ to: 1 });
  const progressLinear = interpolate(frame, [0, durationFrames], [0, 1], {
    extrapolateRight: "clamp",
  });
  const progress = easing === "spring" ? progressSpring : progressLinear;

  const displayed = Math.round(value * progress).toLocaleString();

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div
        style={{
          fontSize,
          fontFamily: t.fonts.display,
          fontWeight: 700,
          color: t.colors.fg,
          lineHeight: 1,
        }}
      >
        {prefix}{displayed}{suffix}
      </div>
      {label && (
        <div
          style={{
            marginTop: 12,
            fontSize: 24,
            color: t.colors.mute,
            fontFamily: t.fonts.body,
            letterSpacing: 2,
            textTransform: "uppercase",
          }}
        >
          {label}
        </div>
      )}
    </div>
  );
};
