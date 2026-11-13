import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_SERIF, THEME } from "../graphics/theme";

// A testimonial (or any quoted line) on screen while it is being read: every word lights up and gets underlined on the moment it is spoken,
// so the eye follows the voice. wordTimes / wordEnds are seconds from the start of this graphic (agent/fx_plan.py aligns them to the Whisper words).
export const QuoteUnderline: React.FC<{ text: string; label?: string; wordTimes: number[]; wordEnds: number[] }> = ({ text, label, wordTimes, wordEnds }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  const words = text.split(/\s+/).filter(Boolean);
  const enter = spring({ frame, fps, config: { damping: 15, stiffness: 150, mass: 0.7 } });
  const out = interpolate(frame, [durationInFrames - 9, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  const size = words.length > 16 ? 58 : words.length > 10 ? 68 : 78;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 250, opacity: out }}>
      <div style={{ width: 920, padding: "40px 46px 46px", borderRadius: 36, background: "rgba(8,12,28,0.72)", border: `2px solid ${THEME.cardEdge}`, boxShadow: "0 24px 70px rgba(0,0,0,.5)", transform: `translateY(${(1 - Math.min(1, enter)) * 50}px) scale(${0.94 + 0.06 * Math.min(1, enter)})`, opacity: Math.min(1, enter * 1.5) }}>
        <div style={{ fontFamily: FONT_SERIF, fontSize: 120, lineHeight: 0.6, color: THEME.accent, height: 56 }}>“</div>
        <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 700, fontSize: size, lineHeight: 1.4, color: "#fff" }}>
          {words.map((w, i) => {
            const a = wordTimes[i] ?? 0;
            const b = Math.max(a + 0.15, wordEnds[i] ?? a + 0.3);
            const spoken = t >= a - 0.02;
            const u = interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return (
              <span key={i} style={{ position: "relative", display: "inline-block", marginRight: "0.28em", opacity: spoken ? 1 : 0.35, color: spoken ? "#fff" : "#cfd6f5" }}>
                {w}
                <span style={{ position: "absolute", left: 0, bottom: 4, height: 9, width: "100%", borderRadius: 6, background: `linear-gradient(90deg, ${THEME.accent}, ${THEME.accent2})`, transformOrigin: "0 50%", transform: `scaleX(${u})`, boxShadow: `0 0 14px ${THEME.accent}88` }} />
              </span>
            );
          })}
        </div>
        {label ? <div style={{ marginTop: 22, fontFamily: '"Montserrat", sans-serif', fontWeight: 700, fontSize: 38, color: THEME.muted, letterSpacing: 2 }}>— {label}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
