import React from "react";
import { Img, staticFile } from "remotion";
import { useFrameSpring } from "../hooks/useFrameSpring";
import { defaultTheme } from "../theme";

export interface TitleCardProps {
  logo?: string | React.ReactNode; // path (string) or node
  title: string;
  subtitle?: string;
  footnote?: string;
  background?: React.ReactNode;
}

// Logo + title + subtitle, centered. Fade/rise in.
export const TitleCard: React.FC<TitleCardProps> = ({
  logo,
  title,
  subtitle,
  footnote,
  background,
}) => {
  const t = defaultTheme;
  const opacity = useFrameSpring({ from: 0, to: 1 });
  const y = useFrameSpring({ from: 40, to: 0, damping: 15 });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        background: t.colors.bg,
      }}
    >
      {background && <div style={{ position: "absolute", inset: 0 }}>{background}</div>}
      <div style={{ opacity, transform: `translateY(${y}px)`, textAlign: "center", zIndex: 1 }}>
        {logo && (
          <div style={{ marginBottom: 48 }}>
            {typeof logo === "string" ? (
              <Img src={staticFile(logo)} style={{ height: 80, width: "auto" }} />
            ) : (
              logo
            )}
          </div>
        )}
        <h1
          style={{
            fontFamily: t.fonts.display,
            fontSize: 120,
            fontWeight: 700,
            color: t.colors.fg,
            margin: 0,
            letterSpacing: -2,
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              fontFamily: t.fonts.body,
              fontSize: 32,
              color: t.colors.mute,
              marginTop: 16,
            }}
          >
            {subtitle}
          </p>
        )}
        {footnote && (
          <p
            style={{
              fontFamily: t.fonts.body,
              fontSize: 16,
              color: t.colors.mute,
              marginTop: 64,
              opacity: 0.6,
            }}
          >
            {footnote}
          </p>
        )}
      </div>
    </div>
  );
};
