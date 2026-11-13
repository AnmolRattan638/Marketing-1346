import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { pop } from "../anim";
import { FONT_HEAD, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// A file turns into an extracted folder: items = [file name, folder name]; the extract happens on the second item's word.
export const FileExtract: React.FC<{ at: number; items: string[]; times: number[] }> = ({ at, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [file = "kit.zip", folder = "kit"] = items;
  const ex = times[1] ?? at + 1.4;
  const f = pop(frame, fps, at + 0.2, { damping: 12, stiffness: 220, mass: 0.7 });
  const go = interpolate(frame, [ex * fps - 10, ex * fps + 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const done = pop(frame, fps, ex + 0.5, { damping: 10, stiffness: 260, mass: 0.6 });
  const box = (label: string, kind: "zip" | "dir", scale: number, op: number) => (
    <div style={{ width: 360, textAlign: "center", transform: `scale(${scale})`, opacity: op, fontFamily: FONT_HEAD }}>
      <div style={{ margin: "0 auto", width: 230, height: 270, borderRadius: 30, border: `4px solid ${THEME.accent}`, background: THEME.glowSoft, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 120, position: "relative" }}>
        {kind === "zip" ? <span style={{ fontFamily: "monospace", fontWeight: 900, fontSize: 40, color: THEME.accent }}>ZIP</span> : <span style={{ fontFamily: "monospace", fontWeight: 900, fontSize: 56, color: THEME.accent }}>{"</>"}</span>}
        {kind === "dir" ? <div style={{ position: "absolute", right: -26, bottom: -26, width: 78, height: 78, borderRadius: 39, background: THEME.ok, color: THEME.ink, fontSize: 52, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${0.3 + 0.7 * done})` }}>✓</div> : null}
      </div>
      <div style={{ marginTop: 26, fontSize: 38, fontWeight: 800 }}>{label}</div>
    </div>
  );
  return (
    <WindowCard at={at} height={560}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 20 }}>
        {box(file, "zip", 0.6 + 0.4 * f - 0.15 * go, 1 - 0.55 * go)}
        <div style={{ fontSize: 96, color: THEME.accent, opacity: 0.4 + 0.6 * go, transform: `translateX(${go * 20}px)`, fontFamily: FONT_HEAD, fontWeight: 900 }}>➜</div>
        {box(folder, "dir", 0.6 + 0.4 * go, go)}
      </div>
    </WindowCard>
  );
};
