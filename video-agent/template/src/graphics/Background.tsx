import React from "react";
import { AbsoluteFill, random, useCurrentFrame, useVideoConfig } from "remotion";
import { FX, LOOK, THEME } from "./theme";

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
          : `linear-gradient(160deg, ${FX.royalDeep}, ${FX.royal} 50%, ${FX.royalDeep})`      // the signature backdrop: deep royal navy, crisp gold light bands on top (no blur)
      }}
    >
      <AbsoluteFill
        style={{
          background: punch
            ? `radial-gradient(circle at 70% 25%, ${THEME.glow}, rgba(240,192,64,0) 55%)`
            : "none",
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
      {!punch ? <Signature t={t} width={width} height={height} /> : null}
      <Pattern kind={LOOK.bg} t={t} width={width} height={height} />
      <AbsoluteFill style={{ display: LOOK.bg === "specks" || LOOK.bg === "aurora" || LOOK.bg === "orbs" ? "block" : "none" }}>
        {specks.map((s, i) => (
          <div key={i} style={{ position: "absolute", left: s.x, top: s.y, width: s.r, height: s.r, borderRadius: "50%", background: THEME.text, opacity: s.o }} />
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,${LOOK.vignette}) 100%)` }} />
    </AbsoluteFill>
  );
};

// One backdrop pattern per art direction (agent/looks.py picks it): every one is built from the theme colours only.
const Pattern: React.FC<{ kind: string; t: number; width: number; height: number }> = ({ kind, t, width, height }) => {
  const line = THEME.text;
  if (kind === "grid") {
    const o = (t * 14) % 90;
    return <AbsoluteFill style={{ opacity: 0.14, backgroundImage: `linear-gradient(${line} 2px, transparent 2px), linear-gradient(90deg, ${line} 2px, transparent 2px)`, backgroundSize: "90px 90px", backgroundPosition: `${o}px ${o}px` }} />;
  }
  if (kind === "dots") {
    return <AbsoluteFill style={{ opacity: 0.22, backgroundImage: `radial-gradient(${line} 3px, transparent 3.5px)`, backgroundSize: "44px 44px", backgroundPosition: `${(t * 12) % 44}px ${(t * 7) % 44}px` }} />;
  }
  if (kind === "stripes") {
    return <AbsoluteFill style={{ opacity: 0.11, backgroundImage: `repeating-linear-gradient(115deg, ${line} 0 36px, transparent 36px 110px)`, backgroundPosition: `${(t * 30) % 146}px 0` }} />;
  }
  if (kind === "rays") {
    return <AbsoluteFill style={{ opacity: 0.24, background: `repeating-conic-gradient(from ${t * 6}deg at 50% 38%, ${THEME.accent} 0deg 7deg, transparent 7deg 24deg)`, WebkitMaskImage: "radial-gradient(circle at 50% 38%, #000 0%, transparent 70%)" }} />;
  }
  if (kind === "aurora") {
    const blob = (cx: number, cy: number, r: number, c: string, ph: number) => (
      <div style={{ position: "absolute", left: cx + Math.sin(t * 0.6 + ph) * 120 - r, top: cy + Math.cos(t * 0.5 + ph) * 160 - r, width: r * 2, height: r * 2, borderRadius: "50%", background: c, filter: "blur(90px)", opacity: 0.35 }} />
    );
    return (
      <AbsoluteFill>
        {blob(width * 0.25, height * 0.3, 380, THEME.accent, 0)}
        {blob(width * 0.8, height * 0.55, 420, THEME.accent2, 2)}
        {blob(width * 0.4, height * 0.85, 360, THEME.hot, 4)}
      </AbsoluteFill>
    );
  }
  if (kind === "shapes") {
    // floating translucent rings and rounded squares drifting upward and turning, seeded so every render is identical
    const items = Array.from({ length: 9 }, (_, i) => {
      const size = 90 + random(`ss${i}`) * 190;
      const x = random(`sx${i}`) * width;
      const y = height - (((random(`sy${i}`) * height) + t * (30 + random(`sv${i}`) * 40)) % (height + size));
      return { size, x, y, rot: t * (12 + random(`sr${i}`) * 20) * (i % 2 ? 1 : -1), ring: i % 3 !== 0 };
    });
    return (
      <AbsoluteFill>
        {items.map((s, i) => (
          <div key={i} style={{ position: "absolute", left: s.x - s.size / 2, top: s.y - s.size / 2, width: s.size, height: s.size, borderRadius: s.ring ? "50%" : 28, border: s.ring ? `5px solid ${THEME.accent}` : "none", background: s.ring ? "none" : THEME.accent2, opacity: s.ring ? 0.22 : 0.12, transform: `rotate(${s.rot}deg)` }} />
        ))}
      </AbsoluteFill>
    );
  }
  if (kind === "waves") {
    const wave = (yBase: number, amp: number, speed: number, ph: number, c: string, o: number) => {
      const pts = Array.from({ length: 28 }, (_, k) => `${(k / 27) * width},${yBase + Math.sin(k * 0.55 + t * speed + ph) * amp}`).join(" ");
      return <polyline key={ph} points={pts} fill="none" stroke={c} strokeWidth={6} strokeLinecap="round" opacity={o} />;
    };
    return (
      <AbsoluteFill>
        <svg width={width} height={height}>
          {wave(height * 0.22, 60, 1.4, 0, THEME.accent, 0.3)}
          {wave(height * 0.5, 80, 1.1, 2, THEME.accent2, 0.24)}
          {wave(height * 0.78, 70, 1.7, 4, THEME.accent, 0.26)}
        </svg>
      </AbsoluteFill>
    );
  }
  if (kind === "scan") {
    // a soft light band sweeping down every few seconds over a faint grid, like a scanner
    const y = ((t * 260) % (height + 600)) - 300;
    return (
      <AbsoluteFill>
        <AbsoluteFill style={{ opacity: 0.1, backgroundImage: `linear-gradient(${line} 2px, transparent 2px), linear-gradient(90deg, ${line} 2px, transparent 2px)`, backgroundSize: "120px 120px" }} />
        <div style={{ position: "absolute", left: 0, right: 0, top: y, height: 300, background: `linear-gradient(180deg, rgba(255,255,255,0), ${THEME.glow}, rgba(255,255,255,0))`, opacity: 0.55 }} />
      </AbsoluteFill>
    );
  }
  return null;
};

// The signature backdrop (navy panels, crisp gold light bands, corner dot grids), after the reference image. The bands sit at the sides and slide very slowly, the centre stays calm so the
// headline and the presenter read clearly. Built from the theme colours only.
const Signature: React.FC<{ t: number; width: number; height: number }> = ({ t, width, height }) => {
  const ANGLE = -40;          // the bands climb to the right, like the reference
  const panel = (cx: number, cy: number, w: number, k: number, o: number) => (
    <div key={`p${k}`} style={{ position: "absolute", left: cx - 800, top: cy - w / 2 + Math.sin(t * 0.3 + k) * 10, width: 1600, height: w, transform: `rotate(${ANGLE}deg)`, background: `linear-gradient(180deg, ${FX.royalLight}, ${FX.royal})`, borderTop: `2px solid ${THEME.glowSoft}`, opacity: o }} />
  );
  const band = (cx: number, cy: number, w: number, o: number, k: number) => {
    const slide = Math.sin(t * 0.5 + k) * 26;
    return (
      <div key={`b${k}`} style={{ position: "absolute", left: cx - 300 + slide, top: cy - w / 2, width: 600, height: w, transform: `rotate(${ANGLE}deg)`, opacity: o * (0.9 + 0.1 * Math.sin(t * 1.3 + k)),
        WebkitMaskImage: cx < width / 2 ? "linear-gradient(90deg, transparent 0%, #000 35%, #000 100%)" : "linear-gradient(90deg, #000 0%, #000 65%, transparent 100%)", background: `linear-gradient(180deg, rgba(0,0,0,0) 0%, ${THEME.accent2} 16%, ${THEME.accent} 50%, ${THEME.accent2} 84%, rgba(0,0,0,0) 100%)`, boxShadow: `0 0 ${Math.round(w * 0.6)}px ${THEME.glowSoft}` }} />
    );
  };
  const dots = (x: number, y: number, w: number, h: number, dir: string) => (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, opacity: 0.55, backgroundImage: `radial-gradient(${THEME.accent2} 2.2px, transparent 2.6px)`, backgroundSize: "30px 30px", backgroundPosition: `${(t * 4) % 30}px 0`,
      WebkitMaskImage: `linear-gradient(${dir}, #000, transparent)`, maskImage: `linear-gradient(${dir}, #000, transparent)` }} />
  );
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {panel(width * 0.05, height * 0.42, 210, 0, 0.3)}
      {panel(width * 0.98, height * 0.2, 260, 1, 0.3)}
      {panel(width * 1.0, height * 0.58, 160, 2, 0.25)}
      {band(width * 0.0, height * 0.46, 56, 0.95, 0)}
      {band(width * 0.0, height * 0.54, 20, 0.9, 1)}
      {band(width * 1.0, height * 0.12, 70, 0.9, 2)}
      {band(width * 1.0, height * 0.2, 14, 0.85, 3)}
      {band(width * 1.0, height * 0.5, 50, 0.9, 4)}
      {dots(0, 0, 330, 380, "135deg")}
      {dots(width - 340, height * 0.28, 340, 420, "225deg")}
    </AbsoluteFill>
  );
};
