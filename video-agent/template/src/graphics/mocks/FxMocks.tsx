import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { blink, clamp01, fade, pop } from "../anim";
import { FONT_HEAD, FONT_MONO, FONT_SERIF, FX, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// The animation-style pool (reference "effects" reel): each one is a mock-up type, appears on its spoken words, brand palette only.
type P = { at: number; title?: string; items: string[]; times: number[] };
const ease = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const glass: React.CSSProperties = { background: "rgba(255,255,255,0.08)", border: "2px solid rgba(255,255,255,0.18)", backdropFilter: "blur(14px)", borderRadius: 34, boxShadow: "0 24px 60px rgba(0,0,0,0.45)" };
const at_ = (p: P, i: number) => p.times[i] ?? p.at + 0.5 + i * 0.6;

// Glass widgets: up to three frosted cards (a big number with a label) that float in one after another.
export const WidgetsFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cards = [0, 2, 4].filter((i) => p.items[i] != null).map((i) => ({ big: p.items[i], label: p.items[i + 1] ?? "", i: i / 2 }));
  return (
    <div style={{ width: 920, display: "flex", flexDirection: "column", gap: 26, fontFamily: FONT_HEAD }}>
      {cards.map((c) => {
        const k = pop(frame, fps, at_(p, c.i), { damping: 14, stiffness: 170, mass: 0.8 });
        const f = Math.sin((frame / fps) * 1.6 + c.i) * 7;
        return (
          <div key={c.i} style={{ ...glass, padding: "34px 44px", opacity: clamp01(k * 2), transform: `translate(${(c.i % 2 ? 1 : -1) * (1 - k) * 160}px, ${f}px) scale(${0.9 + 0.1 * k})`, alignSelf: c.i % 2 ? "flex-end" : "flex-start", width: 700 }}>
            <div style={{ fontSize: 110, fontWeight: 900, color: THEME.accent, lineHeight: 1 }}>{c.big}</div>
            <div style={{ fontSize: 40, color: THEME.text, marginTop: 8 }}>{c.label}</div>
            <div style={{ height: 10, borderRadius: 5, background: "rgba(255,255,255,0.12)", marginTop: 20 }}><div style={{ width: `${ease((frame / fps - at_(p, c.i)) / 1.2) * 78}%`, height: 10, borderRadius: 5, background: THEME.accent }} /></div>
          </div>
        );
      })}
    </div>
  );
};

// The bill: a receipt that prints line by line (items "name|price"), a total at the end.
export const BillFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const rows = p.items.map((s) => s.split("|"));
  const nums = rows.map((r) => parseFloat((r[1] || "0").replace(/[^\d.]/g, "")) || 0);
  const shown = rows.filter((_, i) => t >= at_(p, i)).length;
  const sum = nums.slice(0, shown).reduce((a, b) => a + b, 0);
  const sl = ease((t - p.at) / 0.6);
  return (
    <div style={{ width: 640, background: FX.paper, color: FX.paperInk, fontFamily: FONT_MONO, padding: "46px 44px", transform: `translateY(${(1 - sl) * -200}px) rotate(${-1.5 * sl}deg)`, opacity: sl, boxShadow: "0 30px 70px rgba(0,0,0,0.55)", clipPath: "polygon(0 0,100% 0,100% 100%,96% 98%,92% 100%,88% 98%,84% 100%,80% 98%,76% 100%,72% 98%,68% 100%,64% 98%,60% 100%,56% 98%,52% 100%,48% 98%,44% 100%,40% 98%,36% 100%,32% 98%,28% 100%,24% 98%,20% 100%,16% 98%,12% 100%,8% 98%,4% 100%,0 98%)" }}>
      <div style={{ fontSize: 44, fontWeight: 800, textAlign: "center", letterSpacing: 4 }}>{(p.title || "THE BILL").toUpperCase()}</div>
      <div style={{ borderTop: `3px dashed ${FX.paperInk}`, margin: "18px 0" }} />
      {rows.map((r, i) => (
        <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 38, padding: "7px 0", opacity: t >= at_(p, i) ? 1 : 0 }}>
          <span>{r[0]}</span>
          <span>{r[1] ?? ""}</span>
        </div>
      ))}
      <div style={{ borderTop: `3px dashed ${FX.paperInk}`, margin: "18px 0" }} />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 46, fontWeight: 800, opacity: shown ? 1 : 0 }}>
        <span>TOTAL</span>
        <span>{nums.some((n) => n) ? sum.toFixed(sum % 1 ? 2 : 0) : ""}</span>
      </div>
    </div>
  );
};

// Reject stamp: a card (items[0]) and a stamp word (items[1], default REJECTED) that slams on the spoken word.
export const StampFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const hit = p.times[0] ?? p.at + 1;
  const k = clamp01((t - hit) / 0.12);
  const shake = t >= hit && t < hit + 0.25 ? Math.sin(t * 90) * 8 * (1 - (t - hit) / 0.25) : 0;
  return (
    <div style={{ transform: `translate(${shake}px,${shake * 0.6}px)`, fontFamily: FONT_HEAD }}>
      <WindowCard at={p.at} height={430} title={p.title || "Application"}>
        <div style={{ fontSize: 60, fontWeight: 800, color: THEME.text, marginTop: 20 }}>{p.items[0] || "Your request"}</div>
        <div style={{ marginTop: 22, display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 10 }}>{Array.from({ length: 18 }).map((_, i) => <div key={i} style={{ height: 26, borderRadius: 8, background: i % 5 === 0 ? THEME.accent2 : "rgba(255,255,255,0.12)" }} />)}</div>
      </WindowCard>
      <div style={{ position: "absolute", left: 90, top: 210, border: `14px solid ${THEME.accent}`, color: THEME.accent, borderRadius: 18, padding: "6px 34px", fontSize: 130, fontWeight: 900, letterSpacing: 6, opacity: k, transform: `rotate(-12deg) scale(${2.4 - 1.4 * k})`, background: "rgba(6,8,13,0.55)" }}>{(p.items[1] || "REJECTED").toUpperCase()}</div>
    </div>
  );
};

// Tier list: rows S..D; each item drops into the next tier on its word.
export const TierFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tiers = ["S", "A", "B", "C", "D"];
  const col = [THEME.accent, THEME.hot, THEME.accent2, FX.tierC, FX.tierD];
  return (
    <div style={{ width: 920, fontFamily: FONT_HEAD }}>
      {tiers.map((tn, r) => {
        const it = p.items[r];
        const k = it ? pop(frame, fps, at_(p, r), { damping: 11, stiffness: 260, mass: 0.6 }) : 0;
        const rowIn = fade(frame, fps, p.at + r * 0.08, 0.3);
        return (
          <div key={tn} style={{ display: "flex", height: 128, marginBottom: 12, borderRadius: 18, overflow: "hidden", opacity: rowIn, background: THEME.card, border: `2px solid ${THEME.cardEdge}` }}>
            <div style={{ width: 128, background: col[r], color: THEME.ink, fontSize: 80, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>{tn}</div>
            <div style={{ flex: 1, display: "flex", alignItems: "center", paddingLeft: 30 }}>{it ? <div style={{ fontSize: 48, fontWeight: 800, color: THEME.text, padding: "8px 26px", borderRadius: 14, background: "rgba(255,255,255,0.1)", transform: `translateY(${(1 - k) * -140}px) scale(${0.8 + 0.2 * k})`, opacity: clamp01(k * 2) }}>{it}</div> : null}</div>
          </div>
        );
      })}
    </div>
  );
};

// Profile wall: a grid of profile tiles filling in; the last one is highlighted with a counter.
export const WallFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = 12;
  const names = p.items.length ? p.items : ["ar", "ok", "sk", "mj", "dt", "pk"];
  return (
    <div style={{ width: 940, fontFamily: FONT_HEAD }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 22 }}>
        {Array.from({ length: n }).map((_, i) => {
          const k = pop(frame, fps, p.at + 0.1 + i * 0.12, { damping: 13, stiffness: 220, mass: 0.6 });
          const on = i === n - 1 ? 1 : 0;
          return (
            <div key={i} style={{ height: 250, borderRadius: 26, background: on ? `linear-gradient(160deg,${THEME.accent},${THEME.accent2})` : THEME.card, border: `2px solid ${on ? THEME.hot : THEME.cardEdge}`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", transform: `scale(${0.6 + 0.4 * k})`, opacity: clamp01(k * 2) }}>
              <div style={{ width: 96, height: 96, borderRadius: 48, background: on ? THEME.ink : `linear-gradient(135deg,${THEME.accent2},${THEME.accent})`, color: on ? THEME.accent : THEME.ink, fontSize: 48, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>{(names[i % names.length] || "a")[0].toUpperCase()}</div>
              <div style={{ marginTop: 14, fontSize: 32, fontWeight: 700, color: on ? THEME.ink : THEME.muted }}>{on ? (p.title || "You") : `@${names[i % names.length]}`}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Phone fan: three phones fan out from one point, each with a short line (items).
export const PhoneFanFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const angles = [-16, 0, 16];
  return (
    <div style={{ position: "relative", width: 940, height: 980, fontFamily: FONT_HEAD }}>
      {[0, 1, 2].map((i) => {
        const k = pop(frame, fps, at_(p, i), { damping: 14, stiffness: 150, mass: 0.9 });
        const txt = p.items[i] || "";
        return (
          <div key={i} style={{ position: "absolute", left: 470 - 215 + (i - 1) * 250 * k, top: 80 + Math.abs(i - 1) * 40, width: 430, height: 820, borderRadius: 56, background: THEME.ink, border: `8px solid ${THEME.cardEdge}`, boxShadow: "0 30px 70px rgba(0,0,0,0.6)", transform: `rotate(${angles[i] * k}deg)`, transformOrigin: "50% 100%", opacity: clamp01(k * 2), zIndex: i === 1 ? 2 : 1, overflow: "hidden" }}>
            <div style={{ height: "100%", background: `linear-gradient(170deg,${THEME.card},${THEME.bgBottom})`, display: "flex", alignItems: "center", justifyContent: "center", padding: 34, textAlign: "center", fontSize: 52, fontWeight: 800, color: THEME.text }}><span>{txt}</span></div>
            <div style={{ position: "absolute", top: 14, left: "50%", width: 120, height: 14, borderRadius: 7, background: THEME.cardEdge, transform: "translateX(-50%)" }} />
          </div>
        );
      })}
    </div>
  );
};

// Pullback: a phone showing the line fills the frame, then pulls back to reveal a feed of posts around it.
export const PullbackFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const k = ease((t - (p.times[0] ?? p.at + 1)) / 1.3);
  const s = 2.1 - 1.1 * k;
  return (
    <div style={{ position: "relative", width: 940, height: 1000, fontFamily: FONT_HEAD }}>
      <div style={{ position: "absolute", inset: 0, display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 24, opacity: k, transform: `scale(${0.95 + 0.05 * k})` }}>
        {Array.from({ length: 9 }).map((_, i) => <div key={i} style={{ height: 300, borderRadius: 22, background: i % 2 ? THEME.card : `linear-gradient(160deg,${THEME.accent2}55,${THEME.card})`, border: `2px solid ${THEME.cardEdge}` }} />)}
      </div>
      <div style={{ position: "absolute", left: 470 - 220, top: 40, width: 440, height: 900, borderRadius: 58, background: THEME.ink, border: `8px solid ${THEME.cardEdge}`, transform: `scale(${s})`, transformOrigin: "50% 40%", boxShadow: "0 30px 80px rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", padding: 34, textAlign: "center", opacity: fade(frame, fps, p.at, 0.25) }}>
        <div style={{ fontSize: 58, fontWeight: 800, color: THEME.text }}>{p.items[0] || p.title || "Watch this"}</div>
      </div>
    </div>
  );
};

// Countdown: flip-style clock counting down from items[0] ("02:17") to zero over the scene.
export const CountdownFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const [m, s] = (p.items[0] || "00:10").split(":").map((x) => parseInt(x, 10) || 0);
  const start = m * 60 + s;
  const run = Math.max(1, durationInFrames / fps - p.at - 0.4);
  const left = Math.max(0, Math.round(start * (1 - clamp01((frame / fps - p.at) / run))));
  const d = [Math.floor(left / 60 / 10), Math.floor(left / 60) % 10, Math.floor((left % 60) / 10), left % 10];
  const k = pop(frame, fps, p.at, { damping: 14, stiffness: 180, mass: 0.7 });
  const box = (v: number, key: number) => <div key={key} style={{ width: 190, height: 280, borderRadius: 26, background: FX.clock, border: `2px solid ${FX.clockEdge}`, color: THEME.text, fontSize: 230, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 20px 50px rgba(0,0,0,0.6)", position: "relative" }}>{v}<div style={{ position: "absolute", left: 0, right: 0, top: "50%", height: 4, background: THEME.ink }} /></div>;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 18, transform: `scale(${0.7 + 0.3 * k})`, opacity: clamp01(k * 2), fontFamily: FONT_HEAD }}>
      {box(d[0], 0)}{box(d[1], 1)}
      <div style={{ fontSize: 150, fontWeight: 900, color: THEME.accent, opacity: blink(frame, fps) ? 1 : 0.35 }}>:</div>
      {box(d[2], 2)}{box(d[3], 3)}
    </div>
  );
};

// Shortcut rain: key caps fall and pile up (items = key labels), the last one lights gold.
export const KeyRainFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const keys = p.items.length ? p.items : ["cmd", "shift", "esc", "tab", "enter", "opt", "ctrl", "Z", "K", "V"];
  return (
    <div style={{ position: "relative", width: 960, height: 980, fontFamily: FONT_MONO }}>
      {keys.map((kk, i) => {
        const t0 = p.at + i * 0.18;
        const fall = ease((t - t0) / 0.55);
        const x = ((i * 337) % 760) + 20, rest = 880 - Math.floor(i / 4) * 120, rot = ((i * 53) % 40) - 20;
        const bounce = t > t0 + 0.55 ? Math.max(0, Math.sin((t - t0 - 0.55) * 14) * 14 * Math.exp(-(t - t0 - 0.55) * 6)) : 0;
        return <div key={i} style={{ position: "absolute", left: x, top: -200 + (rest + 200) * fall - bounce, transform: `rotate(${rot * fall}deg)`, opacity: t >= t0 ? 1 : 0, padding: "18px 34px", minWidth: 120, textAlign: "center", fontSize: 48, fontWeight: 800, borderRadius: 18, background: i === keys.length - 1 ? THEME.accent : FX.keycap, color: THEME.ink, boxShadow: `0 8px 0 ${FX.keycapEdge}, 0 18px 30px rgba(0,0,0,0.5)` }}>{kk}</div>;
      })}
    </div>
  );
};

// Digital zoom: a camera viewfinder (REC dot, timecode, corner marks, zoom readout) around a line; the frame zooms in.
export const ViewfinderFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const z = 1 + 0.6 * ease((t - p.at) / 1.6);
  const tc = `00:${String(Math.floor(t) % 60).padStart(2, "0")}:${String(Math.floor((t % 1) * 30)).padStart(2, "0")}`;
  const mark = (s: React.CSSProperties) => <div style={{ position: "absolute", width: 90, height: 90, borderColor: THEME.text, borderStyle: "solid", borderWidth: 0, ...s }} />;
  return (
    <div style={{ position: "relative", width: 940, height: 900, fontFamily: FONT_MONO, opacity: fade(frame, fps, p.at, 0.2) }}>
      {mark({ left: 0, top: 0, borderLeftWidth: 8, borderTopWidth: 8 })}{mark({ right: 0, top: 0, borderRightWidth: 8, borderTopWidth: 8 })}{mark({ left: 0, bottom: 0, borderLeftWidth: 8, borderBottomWidth: 8 })}{mark({ right: 0, bottom: 0, borderRightWidth: 8, borderBottomWidth: 8 })}
      <div style={{ position: "absolute", left: 30, top: 24, display: "flex", gap: 14, alignItems: "center", fontSize: 36, color: THEME.text }}><div style={{ width: 24, height: 24, borderRadius: 12, background: THEME.hot, opacity: blink(frame, fps) ? 1 : 0.2 }} />REC {tc}</div>
      <div style={{ position: "absolute", right: 30, bottom: 24, fontSize: 36, color: THEME.accent }}>x{z.toFixed(1)}</div>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${z})`, fontFamily: FONT_HEAD, fontSize: 96, fontWeight: 900, color: THEME.text, textAlign: "center", padding: "0 90px", lineHeight: 1.05 }}>{p.items[0] || p.title || "Look closer"}</div>
    </div>
  );
};

// Locked on: four brackets snap onto a word (items[0]) with a LOCKED tag.
export const LockOnFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const hit = p.times[0] ?? p.at + 0.9;
  const k = ease((t - (hit - 0.7)) / 0.7);
  const off = 220 * (1 - k);
  const done = t >= hit;
  const c = done ? THEME.accent : THEME.text;
  const br = (x: number, y: number) => <div style={{ position: "absolute", [x ? "right" : "left"]: -off - 40, [y ? "bottom" : "top"]: -off - 30, width: 70, height: 70, borderStyle: "solid", borderColor: c, borderWidth: 0, [`border${x ? "Right" : "Left"}Width`]: 9, [`border${y ? "Bottom" : "Top"}Width`]: 9 } as React.CSSProperties} />;
  return (
    <div style={{ position: "relative", padding: "50px 80px", fontFamily: FONT_HEAD, opacity: fade(frame, fps, p.at, 0.2) }}>
      <div style={{ fontSize: 180, fontWeight: 900, color: THEME.text, letterSpacing: 2 }}>{(p.items[0] || p.title || "THIS").toUpperCase()}</div>
      {br(0, 0)}{br(1, 0)}{br(0, 1)}{br(1, 1)}
      <div style={{ position: "absolute", left: "50%", bottom: -96, transform: "translateX(-50%)", fontFamily: FONT_MONO, fontSize: 38, fontWeight: 800, padding: "6px 22px", background: done ? THEME.accent : "transparent", color: done ? THEME.ink : THEME.text, borderRadius: 8, opacity: clamp01(k * 2) }}>{done ? "LOCKED" : "TRACKING..."}</div>
    </div>
  );
};

// Rabbit hole: nested rounded frames shrink toward the centre, each arriving in turn; the line sits in the innermost.
export const RabbitFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = 5;
  return (
    <div style={{ position: "relative", width: 900, height: 900, fontFamily: FONT_HEAD }}>
      {Array.from({ length: n }).map((_, i) => {
        const k = pop(frame, fps, p.at + i * 0.14, { damping: 15, stiffness: 160, mass: 0.8 });
        const size = 900 - i * 140;
        const sway = Math.sin(frame / fps * 1.3 + i * 0.6) * 10 * (i + 1) * 0.3;
        return <div key={i} style={{ position: "absolute", left: (900 - size) / 2 + sway, top: (900 - size) / 2, width: size, height: size, borderRadius: 40, border: `6px solid ${i % 2 ? THEME.accent2 : THEME.text}`, opacity: clamp01(k * 1.6) * (0.35 + i * 0.13), transform: `scale(${1.5 - 0.5 * k}) rotate(${(1 - k) * (i % 2 ? 14 : -14)}deg)` }} />;
      })}
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", fontSize: 76, fontWeight: 900, color: THEME.text, padding: "0 260px", opacity: fade(frame, fps, p.at + 0.6, 0.3) }}>{p.items[0] || p.title || "deeper"}</div>
    </div>
  );
};

// Giant captions: a huge stacked word (items[0], heavy) over a script-italic second word (items[1]) that overlaps it.
export const GiantFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = pop(frame, fps, p.at, { damping: 12, stiffness: 190, mass: 0.7 });
  const b = pop(frame, fps, at_(p, 1), { damping: 14, stiffness: 150, mass: 0.8 });
  return (
    <div style={{ width: 980, textAlign: "center", lineHeight: 0.85 }}>
      <div style={{ fontFamily: FONT_HEAD, fontSize: 250, fontWeight: 900, color: THEME.accent, letterSpacing: -6, textTransform: "uppercase", transform: `scale(${0.6 + 0.4 * a})`, opacity: clamp01(a * 2) }}>{p.items[0] || "GIANT"}</div>
      <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontSize: 220, color: THEME.text, marginTop: -60, transform: `translateY(${(1 - b) * 120}px) rotate(-4deg)`, opacity: clamp01(b * 2), textShadow: "0 8px 30px rgba(0,0,0,0.6)" }}>{p.items[1] || "captions"}</div>
    </div>
  );
};

// Collage word: one giant gold word with a smaller white block of lines under it (the red-collage reference, in the brand palette).
export const CollageFx: React.FC<P> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = pop(frame, fps, p.at, { damping: 13, stiffness: 200, mass: 0.7 });
  const lines = p.items.slice(1);
  return (
    <div style={{ width: 960, fontFamily: FONT_HEAD }}>
      <div style={{ fontSize: 330, fontWeight: 900, color: THEME.accent, lineHeight: 0.9, letterSpacing: -10, textTransform: "uppercase", transform: `scaleY(${0.5 + 0.5 * a})`, transformOrigin: "0 100%", opacity: clamp01(a * 2), textShadow: `0 0 60px ${THEME.glow}` }}>{p.items[0] || "FREE"}</div>
      {lines.map((l, i) => <div key={i} style={{ fontSize: 84, fontWeight: 900, color: i % 2 ? THEME.accent2 : THEME.text, lineHeight: 1.05, textTransform: "uppercase", opacity: fade(frame, fps, at_(p, i + 1), 0.2), transform: `translateX(${(1 - ease((frame / fps - at_(p, i + 1)) / 0.35)) * -90}px)` }}>{l}</div>)}
    </div>
  );
};
