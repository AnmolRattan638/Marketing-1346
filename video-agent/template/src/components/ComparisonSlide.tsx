import React from "react";
import { defaultTheme } from "../theme";

export interface ComparisonSlideProps {
  left: React.ReactNode;
  right: React.ReactNode;
  leftLabel?: string;
  rightLabel?: string;
  activeSide?: "left" | "right" | "both";
}

// Left-vs-right layout. Non-active side fades to mute color.
export const ComparisonSlide: React.FC<ComparisonSlideProps> = ({
  left,
  right,
  leftLabel,
  rightLabel,
  activeSide = "both",
}) => {
  const t = defaultTheme;
  const leftOpacity = activeSide === "right" ? 0.25 : 1;
  const rightOpacity = activeSide === "left" ? 0.25 : 1;

  const column = (node: React.ReactNode, label: string | undefined, opacity: number) => (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 48,
        opacity,
      }}
    >
      {label && (
        <div
          style={{
            marginBottom: 24,
            fontSize: 18,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: t.colors.mute,
            fontFamily: t.fonts.body,
          }}
        >
          {label}
        </div>
      )}
      <div>{node}</div>
    </div>
  );

  return (
    <div style={{ display: "flex", width: "100%", height: "100%" }}>
      {column(left, leftLabel, leftOpacity)}
      <div style={{ width: 1, background: t.colors.mute, opacity: 0.3 }} />
      {column(right, rightLabel, rightOpacity)}
    </div>
  );
};
