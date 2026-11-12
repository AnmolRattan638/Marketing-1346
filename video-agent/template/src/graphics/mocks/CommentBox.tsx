import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { blink, pop, typed } from "../anim";
import { FONT_HEAD, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// Comment box: the comment is typed on its word, POST is pressed when the typing ends, then the comment lands as a posted row.
export const CommentBox: React.FC<{ at: number; text: string; typeAt: number; pressAt: number }> = ({ at, text, typeAt, pressAt }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pressed = t >= pressAt;
  const press = interpolate(frame, [pressAt * fps, pressAt * fps + 3, pressAt * fps + 8], [1, 0.88, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const posted = pop(frame, fps, pressAt + 0.15, { damping: 13, stiffness: 220, mass: 0.7 });
  return (
    <WindowCard at={at} title="comments" height={520}>
      <div style={{ display: "flex", alignItems: "center", gap: 20, background: "rgba(255,255,255,0.07)", border: `2px solid ${THEME.cardEdge}`, borderRadius: 60, padding: "18px 22px", fontFamily: FONT_HEAD }}>
        <div style={{ width: 64, height: 64, borderRadius: 32, background: `linear-gradient(135deg, ${THEME.accent}, ${THEME.accent2})`, flexShrink: 0 }} />
        <div style={{ flex: 1, fontSize: 44, fontWeight: 700, color: pressed ? "transparent" : "#fff", whiteSpace: "nowrap", overflow: "hidden" }}>
          {typed(text, frame, fps, typeAt)}
          {!pressed && blink(frame, fps) ? <span style={{ color: THEME.accent }}>|</span> : null}
        </div>
        <div style={{ transform: `scale(${press})`, background: pressed ? THEME.ok : THEME.accent, color: THEME.ink, fontWeight: 900, fontSize: 34, padding: "16px 34px", borderRadius: 40 }}>POST</div>
      </div>
      <div style={{ marginTop: 40, opacity: Math.min(1, posted * 2), transform: `translateY(${(1 - posted) * 40}px)`, display: "flex", gap: 20, alignItems: "flex-start" }}>
        <div style={{ width: 64, height: 64, borderRadius: 32, background: `linear-gradient(135deg, ${THEME.accent}, ${THEME.accent2})`, flexShrink: 0 }} />
        <div style={{ fontFamily: FONT_HEAD }}>
          <div style={{ fontSize: 30, fontWeight: 700, color: THEME.muted }}>you · just now</div>
          <div style={{ fontSize: 46, fontWeight: 800 }}>{text}</div>
        </div>
      </div>
    </WindowCard>
  );
};
