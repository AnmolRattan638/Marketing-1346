// Caption styles taken from the two reference reels (config: reference_styles.json). Brand palette only (gold / ice-white on navy); the references' yellow, neon pink and green become THEME colours.
// Styles that need a subject cut-out in the reference (behind-head, arc orbit, giant behind, outline run) use the "no mask" fallback layout: in front of the speaker.
import React from "react";
import { AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_SERIF, THEME } from "../graphics/theme";
import { Box, MONO, Props, SANS, keywordIndex, useChunk } from "./captionKit";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const SHADOW = "0 4px 16px rgba(0,0,0,.7)";
const GOLD_TEXT = `linear-gradient(180deg,${THEME.hot} 0%,${THEME.accent} 55%,${THEME.accent2} 100%)`;
const up = (s: string, on: boolean) => (on ? s.toUpperCase() : s);
type Anchor = { top?: number; bottom?: number; left?: number; right?: number; center?: boolean };
const At: React.FC<{ a: Anchor; children: React.ReactNode }> = ({ a, children }) => (
  <AbsoluteFill style={{ justifyContent: a.top !== undefined ? "flex-start" : "flex-end", alignItems: a.center === false ? (a.left !== undefined ? "flex-start" : "flex-end") : "center", paddingTop: a.top, paddingBottom: a.bottom, paddingLeft: a.left, paddingRight: a.right }}>{children}</AbsoluteFill>
);

// 1. base word caption: small, over the chest, keyword in the accent colour, instant swap
const Chest: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 22, 0.04, 0.25);
  if (!s) return null;
  const k = keywordIndex(s.chunk, emphasis);
  return (
    <Box bottom={640}>
      <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 56, textAlign: "center", maxWidth: 900, textShadow: SHADOW, opacity: 1 - s.outP }}>
        {s.chunk.map((w, i) => <span key={i} style={{ margin: "0 0.16em", color: i === k ? THEME.accent : THEME.text }}>{w.text}</span>)}
      </div>
    </Box>
  );
};

// 2. glass widgets: the phrase in a frosted pill, the last word drops out below as gold italic serif
const Glass: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 24, 0.06, 0.3);
  if (!s) return null;
  const { local, fps, chunk, outP } = s;
  const e = spring({ frame: local, fps, config: { damping: 15, stiffness: 170, mass: 0.7 } });
  const k = keywordIndex(chunk, emphasis);
  const lead = chunk.filter((_, i) => i !== k).map((w) => w.text).join(" ");
  const drop = spring({ frame: local - 6, fps, config: { damping: 11, stiffness: 150, mass: 0.6 } });
  return (
    <At a={{ top: 600 }}>
      <div style={{ opacity: (1 - outP) * Math.min(1, e * 1.5), transform: `translateY(${(1 - Math.min(1, e)) * 40}px)`, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
        {lead ? (
          <div style={{ padding: "22px 40px", borderRadius: 26, background: "rgba(255,255,255,0.16)", backdropFilter: "blur(18px)", border: "2px solid rgba(255,255,255,0.28)", boxShadow: "inset 0 2px 0 rgba(255,255,255,.35), 0 18px 40px rgba(0,0,0,.35)", fontFamily: SANS, fontWeight: 600, fontSize: 56, color: THEME.text }}>{lead}</div>
        ) : null}
        <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 700, fontSize: 112, lineHeight: 1, background: GOLD_TEXT, WebkitBackgroundClip: "text", color: "transparent", filter: `drop-shadow(0 0 22px ${THEME.glow})`, opacity: Math.min(1, drop * 2), transform: `translateY(${(1 - Math.min(1, drop)) * -30}px)` }}>{chunk[k].text}</div>
      </div>
    </At>
  );
};

// 3. behind-head depth (no mask: in front at 85% opacity): small words staggered on a diagonal, the keyword giant gold italic serif with a glow
const Depth: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 24, 0.06, 0.3);
  if (!s) return null;
  const { frame, fps, chunk, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  return (
    <At a={{ top: 520 }}>
      <div style={{ width: 900, opacity: 0.85 * (1 - outP) }}>
        {chunk.map((w, i) => {
          const p = spring({ frame: frame - Math.round(w.start * fps), fps, config: { damping: 14, stiffness: 160, mass: 0.7 } });
          const isK = i === k;
          return (
            <div key={i} style={{ marginLeft: isK ? 120 : i * 150, fontFamily: isK ? FONT_SERIF : SANS, fontStyle: isK ? "italic" : "normal", fontWeight: isK ? 800 : 600, fontSize: isK ? 190 : 66, lineHeight: 1.05, color: isK ? "transparent" : THEME.text, background: isK ? GOLD_TEXT : undefined, WebkitBackgroundClip: isK ? "text" : undefined, filter: isK ? `drop-shadow(0 0 28px ${THEME.glow})` : undefined, opacity: Math.min(1, p * 2), transform: `scale(${0.9 + 0.1 * Math.min(1, p)})`, textShadow: isK ? undefined : SHADOW }}>{w.text}</div>
          );
        })}
      </div>
    </At>
  );
};

// 4. smoke exit: heavy sans, keyword in gold; the phrase before dissolves letter by letter (blur, drift up, spacing grows)
const Smoke: React.FC<Props> = ({ words, emphasis = [], upper = true }) => {
  const s = useChunk(words, 3, 22, 0.05, 0.9);
  if (!s) return null;
  const { t, c, chunk, chunks, fps, frame, local } = s;
  const render = (ch: typeof chunk, ex: number, key: string) => {
    const k = keywordIndex(ch, emphasis);
    let n = 0;
    return (
      <div key={key} style={{ position: "absolute", width: "100%", textAlign: "center", fontFamily: SANS, fontWeight: 800, fontSize: 108, lineHeight: 1.1 }}>
        {ch.map((w, i) => (
          <span key={i} style={{ display: "inline-block", margin: "0 0.18em" }}>
            {up(w.text, upper).split("").map((chr, j) => {
              const d = Math.max(0, Math.min(1, (ex - n++ * 0.025) / 0.55));
              return <span key={j} style={{ display: "inline-block", color: i === k ? THEME.accent : THEME.text, opacity: 1 - d, filter: `blur(${d * 16}px)`, transform: `translateY(${-d * 90}px)`, marginRight: d * 10, textShadow: SHADOW }}>{chr}</span>;
            })}
          </span>
        ))}
      </div>
    );
  };
  const lastEnd = chunk[chunk.length - 1].end;
  const ex = Math.max(0, t - (lastEnd + 0.45));
  const prev = c > 0 ? chunks[c - 1] : null;
  const prevEx = prev ? Math.max(0, t - chunk[0].start + 0.05) : 0;
  const enter = Math.min(1, spring({ frame: local, fps, config: { damping: 18, stiffness: 200 } }));
  return (
    <At a={{ top: 640 }}>
      <div style={{ position: "relative", width: 960, height: 260, opacity: enter }}>
        {prev && prevEx < 0.9 ? render(prev, prevEx * 1.1, "p") : null}
        {render(chunk, ex, "c")}
      </div>
    </At>
  );
};

// 5. wall ink (no wall plane: flat serif with a slight tilt, blur-in like ink soaking), top-left, the last word bigger
const WallInk: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 4, 28, 0.05, 0.35);
  if (!s) return null;
  const { local, fps, chunk, outP } = s;
  const e = Math.min(1, local / (0.4 * fps));
  const k = keywordIndex(chunk, emphasis);
  return (
    <At a={{ top: 400, left: 90, center: false }}>
      <div style={{ maxWidth: 760, fontFamily: FONT_SERIF, fontWeight: 900, fontSize: 84, lineHeight: 1.1, color: THEME.accent2, opacity: (0.3 + 0.7 * e) * (1 - outP) * 0.92, filter: `blur(${(1 - e) * 6}px)`, transform: "rotate(-3deg) perspective(900px) rotateY(-10deg)", textShadow: "0 3px 10px rgba(0,0,0,.55)" }}>
        {chunk.map((w, i) => <span key={i} style={{ margin: "0 0.14em", fontSize: i === k ? 118 : 84, fontStyle: i === k ? "italic" : "normal" }}>{w.text}</span>)}
      </div>
    </At>
  );
};

// 6. arc orbit (no mask: the whole arc in front): words slide along an ellipse around the chest, the keyword bigger and gold
const Orbit: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 24, 0.05, 0.4);
  if (!s) return null;
  const { frame, fps, chunk, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  const n = chunk.length;
  const cx = 540, cy = 1010, rx = 400, ry = 150;
  return (
    <AbsoluteFill style={{ opacity: 1 - outP }}>
      {chunk.map((w, i) => {
        const goal = 0.2 + (n === 1 ? 0.3 : (0.6 * i) / (n - 1));                 // slot on the lower half of the ellipse, left to right
        const p = Math.min(1, Math.max(0, (frame - Math.round(w.start * fps) + 3) / (0.3 * fps)));
        const th = Math.PI * (goal * p + (1 - p) * 0.02);
        const x = cx - rx * Math.cos(th), y = cy + ry * Math.sin(th);
        return <div key={i} style={{ position: "absolute", left: x, top: y, transform: "translate(-50%,-50%)", fontFamily: SANS, fontWeight: 800, fontSize: i === k ? 100 : 64, color: i === k ? THEME.accent : THEME.text, opacity: Math.min(1, p * 2), textShadow: SHADOW, whiteSpace: "nowrap" }}>{w.text}</div>;
      })}
    </AbsoluteFill>
  );
};

// 7. kinetic bounce: stacked words that overshoot in; accent alternates white / gold; the last keyword goes gold italic serif
const Bounce: React.FC<Props> = ({ words, emphasis = [], upper = true }) => {
  const s = useChunk(words, 3, 22, 0.04, 0.35);
  if (!s) return null;
  const { frame, fps, chunk, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  return (
    <At a={{ top: 480 }}>
      <div style={{ textAlign: "center", opacity: 1 - outP, transform: `scale(${1 - outP * 0.15})` }}>
        {chunk.map((w, i) => {
          const p = spring({ frame: frame - Math.round(w.start * fps), fps, config: { damping: 12, stiffness: 180, mass: 0.7 } });
          const hero = i === k && chunk.length > 1;
          return <div key={i} style={{ fontFamily: hero ? FONT_SERIF : SANS, fontStyle: hero ? "italic" : "normal", fontWeight: 900, fontSize: hero ? 150 : 108, lineHeight: 1.05, color: hero ? "transparent" : i % 2 ? THEME.accent : THEME.text, background: hero ? GOLD_TEXT : undefined, WebkitBackgroundClip: hero ? "text" : undefined, opacity: Math.min(1, p * 3), transform: `scale(${0.6 + 0.4 * p})`, textShadow: hero ? undefined : SHADOW }}>{up(w.text, upper && !hero)}</div>;
        })}
      </div>
    </At>
  );
};

// 8. neon wall: rounded bold glow, colour per word, the keyword largest, a little flicker
const Neon: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 22, 0.05, 0.4);
  if (!s) return null;
  const { frame, fps, chunk, local, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  const ramp = Math.min(1, local / (0.25 * fps));
  const flick = random(`neon${Math.floor(frame / 3)}`) > 0.93 ? 0.72 : 1;
  const glow = (c: string) => `0 0 8px ${c}, 0 0 22px ${c}, 0 0 46px ${c}`;
  return (
    <At a={{ top: 560 }}>
      <div style={{ textAlign: "center", maxWidth: 940, opacity: (1 - outP) * ramp * flick, fontFamily: '"Poppins","Nunito",' + SANS, fontWeight: 800 }}>
        {chunk.map((w, i) => {
          const c = i === k ? THEME.accent : i % 2 ? THEME.accent2 : THEME.text;
          return <span key={i} style={{ display: "inline-block", margin: "0 0.2em", fontSize: i === k ? 130 : 72, color: i === k ? THEME.hot : "#fff", textShadow: glow(c) }}>{w.text}</span>;
        })}
      </div>
    </At>
  );
};

// 9. giant behind (no mask: in front, above the head): a huge condensed gold word with small serif connectors; even phrases rise, odd ones drop with letter shards
const Giant: React.FC<Props> = ({ words, emphasis = [], upper = true }) => {
  const s = useChunk(words, 3, 22, 0.04, 0.5);
  if (!s) return null;
  const { t, c, chunk, local, fps, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  const small = chunk.filter((_, i) => i !== k).map((w) => w.text).join(" ");
  const kw = up(chunk[k].text, upper);
  const rise = c % 2 === 0;
  const e = Math.min(1, local / (0.35 * fps));
  const fall = !rise ? Math.max(0, (t - (chunk[chunk.length - 1].end + 0.1)) / 0.5) : 0;
  const size = Math.max(150, Math.min(300, 1500 / Math.max(4, kw.length)));
  return (
    <At a={{ top: 420 }}>
      <div style={{ textAlign: "center", opacity: 1 - outP }}>
        {small ? <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontSize: 60, color: THEME.text, textShadow: SHADOW, marginBottom: -10, opacity: e }}>{small}</div> : null}
        <div style={{ fontFamily: '"Anton","Bebas Neue",' + SANS, fontWeight: 900, fontSize: size, lineHeight: 1, letterSpacing: -2, color: THEME.accent, textShadow: "0 8px 30px rgba(0,0,0,.6)", transform: rise ? `translateY(${(1 - e) * 130}px)` : undefined, opacity: Math.min(1, e * 2) }}>
          {!rise && fall > 0 ? kw.split("").map((ch, j) => <span key={j} style={{ display: "inline-block", transform: `translate(${(random(`x${j}`) - 0.5) * 120 * fall}px, ${fall * fall * (500 + random(`y${j}`) * 250)}px) rotate(${(random(`r${j}`) - 0.5) * 140 * fall}deg)`, opacity: 1 - fall * 0.7 }}>{ch}</span>) : kw}
        </div>
      </div>
    </At>
  );
};

// 10. explosive breakup: white lead + gradient keyword that pops, then bursts into letters, sparks and a ring
const Explode: React.FC<Props> = ({ words, emphasis = [], upper = true }) => {
  const s = useChunk(words, 3, 22, 0.04, 0.6);
  if (!s) return null;
  const { t, chunk, local, fps, inAt } = s;
  const k = keywordIndex(chunk, emphasis);
  const small = chunk.filter((_, i) => i !== k).map((w) => w.text).join(" ");
  const kw = up(chunk[k].text, upper);
  const pop = spring({ frame: local, fps, config: { damping: 11, stiffness: 240, mass: 0.5 } });
  const burstAt = Math.min(chunk[chunk.length - 1].end, inAt + 0.9);
  const b = Math.max(0, Math.min(1, (t - burstAt) / 0.7));
  const size = Math.max(120, Math.min(210, 1500 / Math.max(5, kw.length)));
  return (
    <AbsoluteFill>
      <At a={{ top: 700 }}>
        <div style={{ position: "relative", textAlign: "center" }}>
          {small ? <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 60, color: THEME.text, textShadow: SHADOW, opacity: 1 - b }}>{small}</div> : null}
          <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: size, lineHeight: 1.05, filter: `drop-shadow(0 0 ${20 + b * 30}px ${THEME.glow})` }}>
            {kw.split("").map((ch, j) => {
              const a = random(`a${j}`) * Math.PI * 2, d = (260 + random(`d${j}`) * 380) * b;
              return <span key={j} style={{ display: "inline-block", background: `linear-gradient(180deg,${THEME.hot},${THEME.accent} 50%,${THEME.accent2})`, WebkitBackgroundClip: "text", color: "transparent", transform: `translate(${Math.cos(a) * d}px, ${Math.sin(a) * d}px) rotate(${(random(`q${j}`) - 0.5) * 360 * b}deg) scale(${(0.8 + 0.2 * Math.min(1, pop)) * (1 - b * 0.5)})`, opacity: 1 - b }}>{ch}</span>;
            })}
          </div>
          {b > 0 ? (
            <>
              <div style={{ position: "absolute", left: "50%", top: "62%", width: 700 * b, height: 700 * b, borderRadius: "50%", border: `6px solid ${THEME.hot}`, transform: "translate(-50%,-50%)", opacity: 0.7 * (1 - b) }} />
              {Array.from({ length: 48 }).map((_, j) => {
                const a = random(`sa${j}`) * Math.PI * 2, d = (140 + random(`sd${j}`) * 520) * b;
                return <div key={j} style={{ position: "absolute", left: "50%", top: "62%", width: 10, height: 10, borderRadius: 5, background: j % 3 ? THEME.accent : THEME.hot, transform: `translate(${Math.cos(a) * d}px, ${Math.sin(a) * d + b * b * 120}px)`, opacity: Math.max(0, 1 - b * 1.1) }} />;
              })}
            </>
          ) : null}
        </div>
      </At>
    </AbsoluteFill>
  );
};

// 11. retro typer: typewriter face, letter by letter at speaking speed, block cursor, keyword in gold, a slight tilt
const Retro: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 26, 0.05, 0.5);
  if (!s) return null;
  const { t, chunk, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  let shown = 0;
  const parts = chunk.map((w, i) => {
    const full = w.text + (i < chunk.length - 1 ? " " : "");
    const span = Math.max(0.12, w.end - w.start);
    const n = Math.ceil(full.length * Math.min(1, Math.max(0, (t - w.start + 0.02) / (span * 0.9))));
    shown += n;
    return <span key={i} style={{ color: i === k ? THEME.accent : THEME.text }}>{full.slice(0, n)}</span>;
  });
  return (
    <At a={{ top: 640 }}>
      <div style={{ fontFamily: '"Special Elite","Courier Prime",' + MONO, fontWeight: 700, fontSize: 70, textShadow: SHADOW, transform: "rotate(-1deg)", filter: "blur(0.4px)", opacity: 1 - outP }}>
        {parts}
        <span style={{ opacity: Math.floor(t * 2) % 2 === 0 || shown === 0 ? 1 : 0, color: THEME.accent }}>█</span>
      </div>
    </At>
  );
};

// 12. outline run (no silhouette): the phrase curves over the head on an arc, the keyword in gold
const Outline: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 4, 30, 0.05, 0.4);
  if (!s) return null;
  const { local, fps, chunk, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  const e = Math.min(1, local / (0.4 * fps));
  return (
    <AbsoluteFill style={{ opacity: (1 - outP) * Math.min(1, e * 2) }}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920">
        <defs><path id="arcpath" d="M 110 640 Q 540 380 970 640" /></defs>
        <text fontFamily={SANS} fontWeight={800} fontSize={68} textAnchor="middle" style={{ filter: "drop-shadow(0 4px 12px rgba(0,0,0,.7))" }}>
          <textPath href="#arcpath" startOffset="50%">
            {chunk.map((w, i) => <tspan key={i} fill={i === k ? THEME.accent : THEME.text}>{w.text + (i < chunk.length - 1 ? " " : "")}</tspan>)}
          </textPath>
        </text>
      </svg>
    </AbsoluteFill>
  );
};

// 13. hierarchy stack: a white bold sans line over a much larger gold italic serif word with a soft glow
const Hierarchy: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 24, 0.05, 0.35);
  if (!s) return null;
  const { local, fps, chunk, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  const lead = chunk.filter((_, i) => i !== k).map((w) => w.text).join(" ");
  const a = Math.min(1, local / (0.2 * fps));
  const b = Math.min(1, Math.max(0, (local - 4) / (0.3 * fps)));
  return (
    <At a={{ top: 700 }}>
      <div style={{ textAlign: "center", opacity: 1 - outP }}>
        {lead ? <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 70, color: THEME.text, opacity: a, textShadow: SHADOW }}>{lead}</div> : null}
        <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 700, fontSize: 160, lineHeight: 1.05, background: GOLD_TEXT, WebkitBackgroundClip: "text", color: "transparent", filter: `drop-shadow(0 0 24px ${THEME.glow})`, opacity: b, transform: `translateY(${(1 - b) * 20}px)` }}>{chunk[k].text}</div>
      </div>
    </At>
  );
};

// 14. gold CTA keyword: a small white lead and the keyword in metallic gold italic caps with a light sweep (use on the "comment KEYWORD" line)
const GoldCta: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 3, 24, 0.05, 0.5);
  if (!s) return null;
  const { local, fps, chunk, outP } = s;
  const emph = new Set(emphasis.map((x) => x.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "")));
  const k = chunk.findIndex((w) => emph.has(w.text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "")));
  if (k < 0) return <Chest {...{ words, emphasis }} />;
  const lead = chunk.filter((_, i) => i !== k).map((w) => w.text).join(" ");
  const e = Math.min(1, local / (0.3 * fps));
  const sweep = ((local / fps) % 1.6) / 0.8 - 0.3;                         // a light band crossing the word
  return (
    <At a={{ top: 1180 }}>
      <div style={{ textAlign: "center", opacity: 1 - outP, transform: `scale(${0.9 + 0.1 * e})` }}>
        {lead ? <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 52, color: THEME.text, textShadow: SHADOW }}>{lead}</div> : null}
        <div style={{ fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 900, fontSize: 130, textTransform: "uppercase", background: `linear-gradient(105deg,${THEME.accent2} ${sweep * 100 - 30}%,${THEME.hot} ${sweep * 100}%,${THEME.accent2} ${sweep * 100 + 30}%), linear-gradient(180deg,${THEME.accent2},${THEME.hot},${THEME.accent2})`, WebkitBackgroundClip: "text", color: "transparent", filter: "drop-shadow(0 6px 14px rgba(0,0,0,.6))" }}>{chunk[k].text}</div>
      </div>
    </At>
  );
};

// 15. serif phrases placed near the gesture: upright serif, ONE italic keyword per phrase, the phrase jumps between anchors (planner can send `anchors`)
const ANCHORS: Record<string, Anchor> = {
  "top-left": { top: 380, left: 70, center: false }, "top-right": { top: 380, right: 70, center: false }, "mid-left": { top: 860, left: 70, center: false },
  "mid-right": { top: 860, right: 70, center: false }, "low-left": { top: 1250, left: 70, center: false }, "low-right": { top: 1250, right: 70, center: false }, "mid": { top: 860 },
};
const ORDER = ["top-left", "mid-right", "low-left", "top-right", "mid-left", "low-right"];
const SerifFace: React.FC<Props> = ({ words, emphasis = [], anchors }) => {
  const s = useChunk(words, 4, 28, 0.05, 0.35);
  if (!s) return null;
  const { c, chunk, frame, fps, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  const name = (anchors && anchors[c]) || ORDER[c % ORDER.length];
  return (
    <At a={ANCHORS[name] || ANCHORS["mid"]}>
      <div style={{ maxWidth: 620, fontFamily: '"Cormorant Garamond",' + FONT_SERIF, fontWeight: 700, fontSize: 76, lineHeight: 1.1, color: THEME.text, textShadow: "0 2px 8px rgba(0,0,0,.55)", opacity: 1 - outP }}>
        {chunk.map((w, i) => {
          const p = Math.min(1, Math.max(0, (frame - Math.round(w.start * fps)) / (0.15 * fps)));
          return <span key={i} style={{ margin: "0 0.12em", opacity: p, fontStyle: i === k ? "italic" : "normal", fontSize: i === k ? 112 : 76, fontFamily: i === k ? FONT_SERIF : undefined, color: i === k ? THEME.hot : THEME.text }}>{w.text}</span>;
        })}
      </div>
    </At>
  );
};

// 16. quoted term: the thing to look for, in curly quotes, large serif (use on named tools / techniques)
const Quoted: React.FC<Props> = ({ words, emphasis = [] }) => {
  const s = useChunk(words, 2, 22, 0.05, 0.5);
  if (!s) return null;
  const { local, fps, chunk, outP } = s;
  const k = keywordIndex(chunk, emphasis);
  const e = Math.min(1, local / (0.3 * fps));
  return (
    <At a={{ top: 640 }}>
      <div style={{ fontFamily: '"Cormorant Garamond",' + FONT_SERIF, fontWeight: 700, fontSize: 120, color: THEME.text, textShadow: SHADOW, opacity: (1 - outP) * e, transform: `scale(${0.96 + 0.04 * e})` }}>
        <span style={{ color: THEME.accent }}>“</span>{chunk[k].text}<span style={{ color: THEME.accent }}>”</span>
      </div>
    </At>
  );
};

export const REF_CAPTIONS: Record<string, React.FC<Props>> = {
  chest: Chest, glass: Glass, depth: Depth, smoke: Smoke, wallink: WallInk, orbit: Orbit, bounce: Bounce, neon: Neon,
  giant: Giant, explode: Explode, retro: Retro, outline: Outline, hierarchy: Hierarchy, goldcta: GoldCta, serifface: SerifFace, quoted: Quoted,
};
// they sit at their own place on the frame, so the "emptiest zone" shift of the bottom captions does not apply (chest follows the zones like the classic styles)
export const REF_FIXED = new Set(Object.keys(REF_CAPTIONS).filter((k) => k !== "chest"));
