import React from "react";
import { Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { blink, fade, pop, typed } from "../anim";
import { FONT_HEAD, FONT_SERIF, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

const ease = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);

// Progress chip + command bar + checklist (the reference's counter that makes the viewer wait for the end). items = the list, title = the topic. Each row ticks on its spoken word; the chip counts.
export const TrackerCard: React.FC<{ at: number; title?: string; items: string[]; times: number[] }> = ({ at, title, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const done = items.filter((_, i) => t >= (times[i] ?? at + 0.8 + i * 0.7)).length;
  const cur = Math.min(items.length - 1, Math.max(0, done - 1));
  const cmd = `/${(title || "tips").toLowerCase().replace(/\s+/g, "-")} ${(items[cur] || "").toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div style={{ width: 920, fontFamily: FONT_HEAD }}>
      <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 18, opacity: fade(frame, fps, at, 0.3) }}>
        <div style={{ padding: "10px 22px", borderRadius: 999, background: THEME.accent, color: THEME.ink, fontWeight: 800, fontSize: 38 }}>{String(Math.max(1, done)).padStart(2, "0")}/{String(items.length).padStart(2, "0")}</div>
        <div style={{ flex: 1, padding: "12px 24px", borderRadius: 18, background: "rgba(255,255,255,0.08)", border: `2px solid ${THEME.cardEdge}`, fontFamily: '"JetBrains Mono", monospace', fontSize: 34, color: THEME.text }}>{typed(cmd, frame, fps, at + 0.3, 30)}<span style={{ opacity: blink(frame, fps) ? 1 : 0, color: THEME.accent }}>▌</span></div>
      </div>
      <WindowCard at={at + 0.1} height={Math.min(780, 150 + items.length * 108)} title={title || "Notes"}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {items.map((s, i) => {
            const ta = times[i] ?? at + 0.8 + i * 0.7;
            const on = t >= ta, now = i === cur && on;
            const p = pop(frame, fps, ta, { damping: 10, stiffness: 300, mass: 0.5 });
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 22, padding: "12px 20px", borderRadius: 20, background: now ? THEME.glowSoft : "transparent", border: `2px solid ${now ? THEME.accent2 : "transparent"}` }}>
                <div style={{ width: 44, height: 44, borderRadius: 22, border: `3px solid ${on ? THEME.accent : THEME.cardEdge}`, background: on ? THEME.accent : "transparent", display: "flex", alignItems: "center", justifyContent: "center", color: THEME.ink, fontWeight: 900, fontSize: 28, transform: `scale(${on ? 0.8 + 0.2 * p : 1})` }}>{on ? "✓" : ""}</div>
                <div style={{ fontSize: 46, fontWeight: now ? 800 : 600, color: on ? THEME.text : THEME.muted }}>{s}</div>
              </div>
            );
          })}
        </div>
      </WindowCard>
    </div>
  );
};

// Profile card with a pointer that glides to the Follow button and clicks (title = name, items[0] = handle, items[1] = a line). The click lands on times[0].
export const FollowCard: React.FC<{ at: number; title?: string; items: string[]; times: number[] }> = ({ at, title, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const click = times[0] ?? at + 1.2;
  const clicked = t >= click;
  const m = ease((t - (click - 0.9)) / 0.8);
  const ring = clicked ? Math.min(1, (t - click) / 0.5) : 0;
  return (
    <WindowCard at={at} height={470} title="Profile">
      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 30, marginTop: 10 }}>
        <div style={{ width: 130, height: 130, borderRadius: 65, background: `linear-gradient(135deg,${THEME.accent},${THEME.accent2})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 62, fontWeight: 900, color: THEME.ink }}>{(title || "A")[0]}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 56, fontWeight: 800, color: THEME.text }}>{title || "AR Designs"}</div>
          <div style={{ fontSize: 36, color: THEME.muted }}>{items[0] || "@arrdesigns"}</div>
        </div>
      </div>
      {items[1] ? <div style={{ marginTop: 26, fontSize: 40, color: THEME.text, opacity: 0.9 }}>{items[1]}</div> : null}
      <div style={{ position: "absolute", left: 40, right: 40, bottom: 36, height: 96, borderRadius: 22, background: clicked ? "rgba(255,255,255,0.12)" : THEME.accent, color: clicked ? THEME.text : THEME.ink, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 46, fontWeight: 800, transform: `scale(${clicked ? 0.97 : 1})` }}>{clicked ? "Following" : "Follow"}</div>
      {ring > 0 && ring < 1 ? <div style={{ position: "absolute", left: "50%", bottom: 36 + 48, width: 360 * ring, height: 360 * ring, borderRadius: "50%", border: `5px solid ${THEME.hot}`, opacity: 1 - ring, transform: "translate(-50%,50%)" }} /> : null}
      <svg width="54" height="54" viewBox="0 0 24 24" style={{ position: "absolute", left: 60 + (360 - 60) * m + 300 * (1 - m) * 0, top: 40 + (380 - 40) * m, filter: "drop-shadow(0 4px 6px rgba(0,0,0,.5))", transform: `scale(${clicked && t - click < 0.15 ? 0.85 : 1})` }}>
        <path d="M5 3l14 8-6 2 3 6-3 1-3-6-5 4z" fill="#fff" stroke={THEME.ink} strokeWidth="1.2" />
      </svg>
    </WindowCard>
  );
};

// Stickers and badges: a gold starburst (items[0]), a live pill (items[1]), a count badge (items[2]) and a handwritten tilted note (items[3]); each pops on its spoken time.
export const StickersCard: React.FC<{ at: number; items: string[]; times: number[] }> = ({ at, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const P = (i: number) => pop(frame, fps, times[i] ?? at + 0.2 + i * 0.5, { damping: 9, stiffness: 300, mass: 0.5 });
  const star = Array.from({ length: 24 }, (_, i) => { const a = (Math.PI * 2 * i) / 24, r = i % 2 ? 78 : 100; return `${110 + r * Math.cos(a)},${110 + r * Math.sin(a)}`; }).join(" ");
  return (
    <div style={{ position: "relative", width: 920, height: 560, fontFamily: FONT_HEAD }}>
      {items[0] ? <svg width="220" height="220" style={{ position: "absolute", left: 40, top: 20, transform: `rotate(-10deg) scale(${P(0)})` }}><polygon points={star} fill={THEME.accent} /><text x="110" y="128" textAnchor="middle" fontSize="48" fontWeight="900" fill={THEME.ink}>{items[0]}</text></svg> : null}
      {items[1] ? <div style={{ position: "absolute", right: 30, top: 60, padding: "14px 30px", borderRadius: 999, background: "rgba(255,255,255,0.12)", border: `2px solid ${THEME.cardEdge}`, fontSize: 40, fontWeight: 700, color: THEME.text, transform: `scale(${P(1)})` }}><span style={{ display: "inline-block", width: 18, height: 18, borderRadius: 9, background: THEME.accent, marginRight: 14 }} />{items[1]}</div> : null}
      {items[2] ? <div style={{ position: "absolute", left: 120, top: 290, padding: "16px 34px", borderRadius: 22, background: THEME.card, border: `2px solid ${THEME.accent2}`, fontSize: 52, fontWeight: 800, color: THEME.hot, transform: `scale(${P(2)}) rotate(2deg)` }}>{items[2]}</div> : null}
      {items[3] ? <div style={{ position: "absolute", right: 40, top: 400, fontFamily: '"Caveat","Reenie Beanie",cursive', fontSize: 74, color: THEME.accent, transform: `rotate(-8deg) scale(${P(3)})`, textShadow: "0 3px 10px rgba(0,0,0,.6)" }}>{items[3]}</div> : null}
      <div style={{ display: "none", fontFamily: FONT_SERIF }} />
    </div>
  );
};

// A REAL blurred screenshot (assets/proof): items = [tag line, image path, height/width ratio]. The tag states only what the picture shows; a "no reply" stamp lands on the first reveal word.
export const ProofShot: React.FC<{ at: number; items: string[]; times: number[] }> = ({ at, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at, { damping: 15, stiffness: 170, mass: 0.8 });
  const stamp = pop(frame, fps, times[0] ?? at + 1.0, { damping: 9, stiffness: 260, mass: 0.5 });
  const ratio = parseFloat(items[2]) || 0.8;
  const W = 760;
  return (
    <div style={{ width: 920, display: "flex", flexDirection: "column", alignItems: "center", fontFamily: FONT_HEAD }}>
      <div style={{ marginBottom: 18, padding: "10px 22px", borderRadius: 999, background: THEME.glowSoft, border: `2px solid ${THEME.accent2}`, color: THEME.hot, fontSize: 28, fontWeight: 700, letterSpacing: 1, opacity: Math.min(1, p * 2) }}>{items[0]}</div>
      <div style={{ position: "relative", width: W, borderRadius: 30, overflow: "hidden", border: `2px solid ${THEME.cardEdge}`, boxShadow: "0 30px 80px rgba(0,0,0,.55)", opacity: Math.min(1, p * 2.2), transform: `translateY(${(1 - p) * 100}px) scale(${0.92 + 0.08 * p})` }}>
        <Img src={staticFile(items[1])} style={{ width: W, height: W * ratio, display: "block", objectFit: "cover" }} />
        <div style={{ position: "absolute", right: 28, bottom: 30, padding: "12px 26px", borderRadius: 14, background: THEME.accent, color: THEME.ink, fontSize: 40, fontWeight: 900, letterSpacing: 1, transform: `rotate(-6deg) scale(${stamp})`, opacity: Math.min(1, stamp * 3), boxShadow: "0 10px 26px rgba(0,0,0,.5)" }}>NO REPLY</div>
      </div>
    </div>
  );
};
