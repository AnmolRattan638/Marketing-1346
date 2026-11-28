import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_HEAD, LOGO_SAFE_TOP, THEME } from "./theme";

// THE HOOK (hardcoded for scene 1 of every reel): a phone that breaks while the voice speaks. Every spoken word SLAMS in (huge, uppercase), the whole frame
// shakes on each word, a crack spreads across the phone glass, missed-message notifications pile in, numbers/keywords hit harder with a flash, and the
// last 0.45 s tears the frame into glitch slices as the transition into scene 2. No captions here: the slammed words ARE the captions.
// Everything is drawn from the theme colours (RGB-split uses accent + text, not new hues).
export interface HookWord { text: string; start: number; end: number }
export interface HookSpec { notifs: string[]; variant?: "phone" | "slam" | "zig" }      // phone = the breaking phone; slam = no phone, gold bars sweep in on every word; zig = one word per line, alternating sides, an arrow pointing at him

const rnd = (n: number) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const isHeavy = (w: string, emph: string[]) => /\d|%|₹/.test(w) || emph.some((e) => e && w.toLowerCase().includes(e.toLowerCase()));
const clean = (w: string) => w.replace(/[.,!?;:]+$/g, "");

// the biggest font size at which ALL the hook's words still fit in the area above the notifications (greedy line wrap, uppercase Montserrat Black ~0.66 em per letter)
const fitSize = (words: HookWord[], emph: string[], variant?: string): number => {
  const W = 840, H = 400;      // the lane above his head: anything lower would be hidden behind the hood
  if (variant === "zig") {                                    // one word per line: the longest word must fit the width and all the lines the height
    const longest = Math.max(...words.map((w) => clean(w.text).length), 3);
    return Math.max(48, Math.min(150, Math.floor(W / (0.66 * longest + 0.4)), Math.floor(H / (words.length * 1.12))));
  }
  for (const size of [190, 164, 144, 126, 110, 98, 88, 78, 68, 60, 52]) {
    let lines = 1, x = 0;
    for (const w of words) {
      const s = size * (isHeavy(w.text, emph) ? 1.1 : 1);
      const wd = clean(w.text).length * 0.66 * s + s * 0.18;
      if (x + wd > W && x > 0) { lines++; x = 0; }
      x += wd;
    }
    if (lines * size * 1.1 <= H) return size;
  }
  return 52;
};

const cracks = (n: number) => Array.from({ length: n }, (_, k) => {
  const ang = (k / n) * Math.PI * 2 + rnd(k) * 0.7;
  let x = 540 + (rnd(k + 9) - 0.5) * 60, y = 800 + (rnd(k + 5) - 0.5) * 60;
  let d = `M${x.toFixed(0)} ${y.toFixed(0)}`;
  const segs = 4 + Math.floor(rnd(k + 2) * 3);
  for (let s = 0; s < segs; s++) {
    const a = ang + (rnd(k * 7 + s) - 0.5) * 0.9, len = 120 + rnd(k * 3 + s) * 190;
    x += Math.cos(a) * len; y += Math.sin(a) * len;
    d += ` L${x.toFixed(0)} ${y.toFixed(0)}`;
  }
  return d;
});
const CRACKS = cracks(14);

const Board: React.FC<{ words: HookWord[]; emphasis: string[]; notifs: string[]; t: number; frame: number; fps: number; variant?: string }> = ({ words, emphasis, notifs, t, frame, fps, variant = "phone" }) => {
  const shown = words.filter((w) => t >= w.start);
  const n = Math.max(words.length, 1);
  const size = fitSize(words, emphasis, variant);
  const last = shown[shown.length - 1];
  const sinceLast = last ? t - last.start : 99;
  return (
    <AbsoluteFill>
      {variant === "slam" ? (
        <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
          {words.map((w, k) => {
            if (t < w.start) return null;
            const grow = Math.min(1, (t - w.start) * 8), y = LOGO_SAFE_TOP + 40 + (k % 4) * 215, fromLeft = k % 2 === 0;
            return <rect key={k} x={fromLeft ? -40 : 1120 - 1160 * grow} y={y} width={1160 * grow} height={k % 3 === 0 ? 26 : 10} fill={THEME.accent} opacity={0.55} transform={`rotate(-8 540 ${y})`} />;
          })}
        </svg>
      ) : null}
      {variant === "zig" ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: LOGO_SAFE_TOP + 700, textAlign: "center", fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 150, color: THEME.accent, opacity: Math.min(1, t * 2) * (0.6 + 0.4 * Math.sin(t * 8)), transform: `translateY(${Math.sin(t * 6) * 14}px)` }}>↓</div>
      ) : null}
      {/* the phone */}
      {variant === "phone" ? <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
        <rect x={90} y={LOGO_SAFE_TOP} width={900} height={1400} rx={110} fill="rgba(255,255,255,0.03)" stroke={THEME.cardEdge} strokeWidth={10} />
        <rect x={430} y={LOGO_SAFE_TOP + 26} width={220} height={34} rx={17} fill={THEME.cardEdge} />
        {CRACKS.map((d, k) => {
          const w = words[k % n];
          if (!w || t < w.start) return null;
          const grow = Math.min(1, (t - w.start) * 9);
          return <path key={k} d={d} fill="none" stroke={THEME.text} strokeOpacity={0.85} strokeWidth={k % 3 === 0 ? 5 : 3} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - grow} style={{ filter: `drop-shadow(0 0 8px ${THEME.glow})` }} />;
        })}
      </svg> : null}
      {/* the words: each one slams in, the line builds up */}
      <div style={{ position: "absolute", left: 130, right: 130, top: LOGO_SAFE_TOP + 100, display: "flex", flexWrap: variant === "zig" ? "nowrap" : "wrap", flexDirection: variant === "zig" ? "column" : "row", justifyContent: "center", alignContent: "flex-start", alignItems: variant === "zig" ? undefined : undefined, gap: `${size * 0.04}px ${size * 0.18}px` }}>
        {shown.map((w, i) => {
          const age = t - w.start, heavy = isHeavy(w.text, emphasis), newest = w === last;
          const slam = Math.max(0, 1 - age * 11);                              // 1 -> 0 over ~0.09 s
          const scale = 1 + slam * (heavy ? 1.6 : 1.1) + (newest ? Math.max(0, Math.sin(Math.min(1, age * 7) * Math.PI)) * 0.06 : 0);
          const split = Math.max(0, 1 - age * 7) * (heavy ? 22 : 12);
          return (
            <span key={i} style={{ display: "inline-block", alignSelf: variant === "zig" ? (i % 2 ? "flex-end" : "flex-start") : undefined, fontFamily: FONT_HEAD, fontWeight: 900, fontSize: size * (heavy ? 1.1 : 1), lineHeight: 1.04, textTransform: "uppercase", color: heavy ? THEME.accent : THEME.text,
              transform: `scale(${scale}) rotate(${slam * (rnd(i + 3) - 0.5) * 9}deg)`, textShadow: `${split}px 0 ${THEME.accent}, ${-split}px 0 ${THEME.text}, 0 8px 30px rgba(0,0,0,0.6)`, WebkitTextStroke: heavy ? "0" : undefined }}>{clean(w.text)}</span>
          );
        })}
      </div>
      {/* missed-message notifications pile in (generic copy, no figures) */}
      <div style={{ position: "absolute", left: 150, right: 150, top: LOGO_SAFE_TOP + 960 }}>
        {(variant === "phone" ? notifs.slice(0, 3) : []).map((txt, i) => {
          const at = (words[Math.min(n - 1, 1 + i * 2)]?.start ?? 0.6 + i * 0.5);
          const p = Math.min(1, Math.max(0, (t - at) * 6));
          if (p <= 0) return null;
          return <div key={i} style={{ marginBottom: 18, padding: "22px 30px", borderRadius: 26, background: THEME.card, border: `3px solid ${i === 0 ? THEME.accent : THEME.cardEdge}`, color: THEME.text, fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 40,
            opacity: p, transform: `translateX(${(1 - p) * (i % 2 ? 160 : -160)}px) rotate(${(1 - p) * (i % 2 ? 3 : -3)}deg)`, boxShadow: `0 10px 40px rgba(0,0,0,0.45)` }}>{txt}</div>;
        })}
      </div>
      {sinceLast < 99 && null}
    </AbsoluteFill>
  );
};

export const HookBlast: React.FC<{ words: HookWord[]; emphasis?: string[]; spec?: HookSpec; duration: number }> = ({ words, emphasis = [], spec, duration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const notifs = spec?.notifs ?? [];
  // shake envelope: every word kicks the whole frame, heavier words kick harder
  let env = 0, flash = 0;
  for (const w of words) {
    const age = t - w.start;
    if (age < 0 || age > 0.6) continue;
    const heavy = isHeavy(w.text, emphasis);
    env = Math.max(env, Math.exp(-age * 9) * (heavy ? 1.6 : 1));
    flash = Math.max(flash, Math.exp(-age * 22) * (heavy ? 0.5 : 0.18));
  }
  const tear = Math.max(0, (t - (duration - 0.45)) / 0.45);                   // 0 -> 1 over the last 0.45 s
  env = Math.max(env, tear * 1.4);
  const amp = 26;
  const sx = (rnd(frame * 1.7) - 0.5) * 2 * amp * env, sy = (rnd(frame * 2.3 + 8) - 0.5) * 2 * amp * env, sr = (rnd(frame * 3.1 + 2) - 0.5) * 2.4 * env;
  const board = (
    <Board words={words} emphasis={emphasis} notifs={notifs} t={t} frame={frame} fps={fps} variant={spec?.variant} />
  );
  const BANDS = 9;
  const content = tear > 0 ? (
    <AbsoluteFill>
      {Array.from({ length: BANDS }, (_, b) => {
        const top = (b / BANDS) * 100, bottom = 100 - ((b + 1) / BANDS) * 100;
        const dx = (rnd(b * 5 + Math.floor(frame / 2)) - 0.5) * 2 * 260 * tear;
        return <AbsoluteFill key={b} style={{ clipPath: `inset(${top}% 0 ${bottom}% 0)`, transform: `translateX(${dx}px)` }}>{board}</AbsoluteFill>;
      })}
    </AbsoluteFill>
  ) : board;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `translate(${sx}px, ${sy}px) rotate(${sr}deg) scale(${1.04 + env * 0.03})` }}>{content}</AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 42%, ${THEME.text} 0%, ${THEME.accent} 35%, transparent 75%)`, opacity: Math.min(0.9, flash + tear * 0.35), mixBlendMode: "screen" }} />
    </AbsoluteFill>
  );
};
