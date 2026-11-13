import React from "react";
import { AbsoluteFill, random, useCurrentFrame, useVideoConfig } from "remotion";
import { THEME } from "./theme";

// Themed backdrop: gradient, soft glow, a few slowly drifting specks (seeded, so every render is identical), vignette.
// `punch` swaps to the full-colour slide; `ghost` is the giant faint word behind a punch line.
export const Background: React.FC<{ punch?: boolean; ghost?: string }> = ({ punch = false, ghost }) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const t = frame / fps;
  const specks = Array.from({ length: 16 }, (_, i) => {
    const x = random(`x${i}`) * width;
    const y = (random(`y${i}`) * height + t * (10 + random(`v${i}`) * 18)) % height;
    return { x, y, r: 2 + random(`r${i}`) * 4, o: 0.1 + random(`o${i}`) * 0.18 };
  });
  return (
    <AbsoluteFill
      style={{
        background: punch
          ? `linear-gradient(150deg, ${THEME.accent}, ${THEME.accent2} 75%)`
          : `linear-gradient(170deg, ${THEME.bgTop}, ${THEME.bgBottom})`,
      }}
    >
      <AbsoluteFill
        style={{
          background: punch
            ? `radial-gradient(circle at 70% 25%, ${THEME.glow}, rgba(240,192,64,0) 55%)`
            : `radial-gradient(circle at 75% 20%, ${THEME.glowSoft}, rgba(240,192,64,0) 55%), radial-gradient(circle at 15% 85%, rgba(201,168,76,0.08), rgba(201,168,76,0) 50%)`,
        }}
      />
      {ghost ? (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <div
            style={{
              fontFamily: '"Montserrat", "Poppins", Arial, sans-serif',
              fontWeight: 900,
              fontSize: 520,
              lineHeight: 1,
              color: THEME.text,
              opacity: 0.1,
              transform: `translateY(-80px) rotate(-6deg) scale(${1 + 0.02 * Math.sin(t * 0.8)})`,
              whiteSpace: "nowrap",
              textTransform: "uppercase",
            }}
          >
            {ghost}
          </div>
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill>
        {specks.map((s, i) => (
          <div key={i} style={{ position: "absolute", left: s.x, top: s.y, width: s.r, height: s.r, borderRadius: "50%", background: THEME.text, opacity: s.o }} />
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.38) 100%)" }} />
    </AbsoluteFill>
  );
};
