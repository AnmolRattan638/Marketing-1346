import React from "react";
import { Img, staticFile } from "remotion";
import { defaultTheme } from "../theme";

export interface UIFrameProps {
  src?: string; // image path relative to project root
  children?: React.ReactNode;
  variant?: "mac" | "generic";
  url?: string;
  width?: number | string;
  height?: number | string;
}

// A browser/window chrome wrapper around a screenshot or child component.
// Aesthetic-neutral: colors come from theme.
export const UIFrame: React.FC<UIFrameProps> = ({
  src,
  children,
  variant = "mac",
  url,
  width = "80%",
  height = "auto",
}) => {
  const t = defaultTheme;
  const chromeBg = "#1a1a1c";
  const chromeBorder = "#2a2a2d";

  return (
    <div
      style={{
        width,
        height,
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
        background: chromeBg,
        border: `1px solid ${chromeBorder}`,
      }}
    >
      {/* Title bar */}
      <div
        style={{
          height: 36,
          background: chromeBg,
          borderBottom: `1px solid ${chromeBorder}`,
          display: "flex",
          alignItems: "center",
          padding: "0 12px",
          gap: 12,
        }}
      >
        {variant === "mac" && (
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#ff5f57" }} />
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#febc2e" }} />
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#28c840" }} />
          </div>
        )}
        {url && (
          <div
            style={{
              flex: 1,
              background: "#0f0f10",
              borderRadius: 6,
              padding: "4px 12px",
              color: t.colors.mute,
              fontSize: 13,
              fontFamily: t.fonts.mono,
              textAlign: "center",
            }}
          >
            {url}
          </div>
        )}
      </div>
      {/* Body */}
      <div style={{ background: t.colors.bg }}>
        {src ? <Img src={staticFile(src)} style={{ width: "100%", display: "block" }} /> : children}
      </div>
    </div>
  );
};
