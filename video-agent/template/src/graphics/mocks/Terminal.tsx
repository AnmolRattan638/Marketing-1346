import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { blink, fade, pop, typed } from "../anim";
import { FONT_MONO, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// Terminal: "> text" and "$ text" lines are typed, "ok: text" lines appear with a green tick, other lines appear at once. Each line starts on its word.
export const Terminal: React.FC<{ at: number; title?: string; items: string[]; times: number[] }> = ({ at, title, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const shown = items.map((s, i) => ({ s, at: times[i] ?? at + 0.5 + i * 0.6 })).filter((x) => t >= x.at - 0.02);
  const last = shown.length - 1;
  return (
    <WindowCard at={at} title={title ?? "terminal"} dark height={Math.max(520, 180 + items.length * 84)}>
      <div style={{ fontFamily: FONT_MONO, fontSize: 40, lineHeight: 1.7 }}>
        {shown.map((x, i) => {
          const isOk = x.s.startsWith("ok:");
          const isCmd = x.s.startsWith(">") || x.s.startsWith("$");
          const body = isOk ? x.s.slice(3).trim() : x.s;
          const text = isCmd ? typed(body, frame, fps, x.at, 18) : body;
          const p = pop(frame, fps, x.at, { damping: 16, stiffness: 220, mass: 0.6 });
          return (
            <div key={i} style={{ display: "flex", gap: 16, color: isOk ? "#fff" : isCmd ? "#FFD9A0" : THEME.muted, opacity: isCmd ? 1 : Math.min(1, p * 2), transform: isCmd ? undefined : `translateX(${(1 - p) * 30}px)` }}>
              {isOk ? <span style={{ color: THEME.ok, fontWeight: 900 }}>✓</span> : null}
              <span>
                {text}
                {i === last && isCmd && blink(frame, fps) ? <span style={{ background: THEME.hot, color: THEME.hot }}>_</span> : null}
              </span>
            </div>
          );
        })}
        {shown.length === 0 ? <div style={{ color: THEME.hot, opacity: fade(frame, fps, at) }}>$ {blink(frame, fps) ? "▌" : " "}</div> : null}
      </div>
    </WindowCard>
  );
};
