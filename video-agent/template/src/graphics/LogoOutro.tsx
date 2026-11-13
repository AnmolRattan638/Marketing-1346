import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_HEAD, THEME } from "./theme";

// The closing animation: pulse rings expand, the logo springs in and settles, the call to action rises under it. Always the last thing on screen.
export const LogoOutro: React.FC<{ logo?: string; cta?: string }> = ({ logo, cta }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: frame - 3, fps, config: { damping: 9, stiffness: 150, mass: 0.8 } });
  const text = spring({ frame: frame - Math.round(fps * 0.45), fps, config: { damping: 16, stiffness: 160, mass: 0.8 } });
  const ring = (delay: number) => {
    const p = interpolate(frame, [delay, delay + fps * 1.1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return { size: 260 + p * 760, opacity: (1 - p) * 0.55 * (p > 0 ? 1 : 0) };
  };
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      {[2, 9, 16].map((d) => {
        const r = ring(d);
        return <div key={d} style={{ position: "absolute", width: r.size, height: r.size, borderRadius: "50%", border: `5px solid ${THEME.accent}`, opacity: r.opacity }} />;
      })}
      {logo ? (
        <Img src={staticFile(logo)} style={{ width: 340, height: 340, objectFit: "contain", borderRadius: 60, transform: `scale(${0.2 + 0.8 * pop}) rotate(${(1 - pop) * -14}deg)`, opacity: Math.min(1, pop * 2.5), filter: "drop-shadow(0 20px 50px rgba(240,192,64,0.35))" }} />
      ) : null}
      {cta ? (
        <div style={{ position: "absolute", top: "50%", marginTop: 250, width: 900, textAlign: "center", fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 70, color: THEME.text, opacity: Math.min(1, text * 2), transform: `translateY(${(1 - text) * 50}px)`, textShadow: "0 8px 24px rgba(0,0,0,0.5)" }}>
          <span style={{ background: `linear-gradient(135deg, ${THEME.accent}, ${THEME.accent2})`, color: THEME.ink, padding: "10px 36px", borderRadius: 30, display: "inline-block" }}>{cta}</span>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
