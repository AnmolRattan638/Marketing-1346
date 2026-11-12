import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { pop } from "../anim";
import { FONT_HEAD, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// Generic window: rows that slide in, each on its word.
export const WindowRows: React.FC<{ at: number; title?: string; items: string[]; times: number[] }> = ({ at, title, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <WindowCard at={at} title={title} height={Math.min(760, 180 + items.length * 110)}>
      <div style={{ display: "flex", flexDirection: "column", gap: 22, fontFamily: FONT_HEAD }}>
        {items.map((s, i) => {
          const p = pop(frame, fps, times[i] ?? at + 0.5 + i * 0.6, { damping: 15, stiffness: 200, mass: 0.7 });
          return (
            <div key={i} style={{ opacity: Math.min(1, p * 2), transform: `translateX(${(1 - p) * 70}px)`, background: "rgba(255,255,255,0.07)", border: `2px solid ${THEME.cardEdge}`, borderRadius: 24, padding: "20px 30px", fontSize: 48, fontWeight: 800 }}>
              {s}
            </div>
          );
        })}
      </div>
    </WindowCard>
  );
};
