import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { pop } from "./anim";
import { FONT_HEAD, THEME } from "./theme";

// Words that get struck through one by one ("editing / cutting / software ..."): each slides in just before its spoken word, a line is drawn through it on the word.
export const StrikeList: React.FC<{ items: string[]; times: number[] }> = ({ items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const size = items.length > 4 ? 84 : 104;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {items.map((s, i) => {
        const at = times[i] ?? 0.8 + i * 0.7;
        const enter = pop(frame, fps, Math.max(0, at - 0.45), { damping: 15, stiffness: 200, mass: 0.7 });
        const line = interpolate(frame, [at * fps, at * fps + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const struck = frame / fps >= at;
        return (
          <div key={i} style={{ position: "relative", display: "inline-block", alignSelf: "flex-start", opacity: Math.min(1, enter * 2) * (struck ? 0.62 : 1), transform: `translateX(${(1 - enter) * -80}px)` }}>
            <span style={{ fontFamily: FONT_HEAD, fontWeight: 900, fontSize: size, color: THEME.text, textTransform: "uppercase", letterSpacing: -1 }}>{s}</span>
            <div style={{ position: "absolute", left: -10, top: "56%", height: 12, width: `${line * 104}%`, background: THEME.hot, borderRadius: 6, boxShadow: `0 4px 16px ${THEME.glow}` }} />
          </div>
        );
      })}
    </div>
  );
};
