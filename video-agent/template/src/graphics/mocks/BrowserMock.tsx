import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { fade, pop } from "../anim";
import { FONT_HEAD, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// A small website building itself: browser bar, nav, headline, sub line, button, picture block. items = [headline, sub, button], each on its word.
// This is the visual for "your shop gets a website": it shows the thing instead of a stock photo of a person with a laptop.
export const BrowserMock: React.FC<{ at: number; items: string[]; times: number[] }> = ({ at, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [headline = "Your Business", sub = "", button = ""] = items;
  const ta = (i: number, fallback: number) => times[i] ?? at + fallback;
  const h = pop(frame, fps, ta(0, 0.5), { damping: 15, stiffness: 190, mass: 0.7 });
  const s = pop(frame, fps, ta(1, 1.1), { damping: 16, stiffness: 170, mass: 0.8 });
  const b = pop(frame, fps, ta(2, 1.7), { damping: 9, stiffness: 280, mass: 0.6 });
  const nav = fade(frame, fps, at + 0.25, 0.4);
  const pic = fade(frame, fps, at + 0.4, 0.5);
  return (
    <WindowCard at={at} height={720}>
      <div style={{ marginTop: -8, display: "flex", alignItems: "center", gap: 14, background: "rgba(255,255,255,0.08)", borderRadius: 26, padding: "12px 24px", fontFamily: FONT_HEAD, fontSize: 28, color: THEME.muted }}>
        <span style={{ color: THEME.ok }}>🔒</span> yourbusiness.in
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 28, opacity: nav }}>
        <div style={{ width: 54, height: 54, borderRadius: 14, background: THEME.accent }} />
        <div style={{ flex: 1 }} />
        {[110, 90, 130].map((w, i) => (
          <div key={i} style={{ width: w, height: 16, borderRadius: 8, background: "rgba(255,255,255,0.22)" }} />
        ))}
      </div>
      <div style={{ display: "flex", gap: 28, marginTop: 36 }}>
        <div style={{ flex: 1.25, fontFamily: FONT_HEAD }}>
          <div style={{ fontSize: 64, fontWeight: 900, lineHeight: 1.05, opacity: Math.min(1, h * 2), transform: `translateY(${(1 - h) * 40}px)` }}>{headline}</div>
          <div style={{ fontSize: 32, fontWeight: 500, color: THEME.muted, marginTop: 18, lineHeight: 1.3, opacity: Math.min(1, s * 2), transform: `translateY(${(1 - s) * 30}px)` }}>{sub}</div>
          {button ? (
            <div style={{ display: "inline-block", marginTop: 30, background: THEME.accent, color: THEME.ink, fontWeight: 900, fontSize: 34, padding: "16px 36px", borderRadius: 40, transform: `scale(${0.4 + 0.6 * b})`, opacity: Math.min(1, b * 2), transformOrigin: "left center" }}>{button}</div>
          ) : null}
        </div>
        <div style={{ flex: 0.9, height: 330, borderRadius: 28, background: `linear-gradient(140deg, ${THEME.accent2}, ${THEME.hot})`, opacity: pic, transform: `scale(${0.9 + 0.1 * pic})` }} />
      </div>
      <div style={{ display: "flex", gap: 20, marginTop: 34, opacity: fade(frame, fps, ta(2, 1.7) + 0.2, 0.4) }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ flex: 1, height: 70, borderRadius: 20, background: "rgba(255,255,255,0.08)" }} />
        ))}
      </div>
    </WindowCard>
  );
};
