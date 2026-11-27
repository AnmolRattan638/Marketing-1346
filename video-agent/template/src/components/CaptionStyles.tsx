import React from "react";
import { AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Captions } from "./Captions";
import { FONT_SERIF, THEME } from "../graphics/theme";
import { CaptionStyle, CaptionZone, DEFAULT_Y, MONO, Props, SANS, Box, norm, useChunk } from "./captionKit";
import { REF_CAPTIONS, REF_FIXED } from "./RefCaptions";
import { StageContext } from "../graphics/theme";
export type { CaptionStyle, CaptionZone };
export const CAPTION_STYLES: CaptionStyle[] = ["pill", "cinematic", "karaoke", "stack", "typewriter", ...(Object.keys(REF_CAPTIONS) as CaptionStyle[])];


// ---- cinematic: small, spaced, glowing lines that blur in and out; a phrase with an emphasis word becomes a big "hero" treatment ----
type Hero = "gold" | "neon" | "fire";   // names kept; all three are drawn in the brand palette (gold / glowing light / deep gold)
const HEROES: Hero[] = ["gold", "neon", "fire"];

const Cinematic: React.FC<Props> = ({ words, emphasis = [], upper = true, bottom = 400 }) => {
  const s = useChunk(words, 3, 22, 0.08, 0.35);
  if (!s) return null;
  const { frame, fps, t, c, chunk, local, outP, active } = s;
  const emph = new Set(emphasis.map(norm));
  const hero = chunk.some((w) => emph.has(norm(w.text)) || /\d/.test(w.text));
  const enter = spring({ frame: local, fps, config: { damping: 16, stiffness: 140, mass: 0.7 } });
  const blur = (1 - Math.min(1, enter)) * 16 + outP * 14;
  const opacity = Math.min(1, enter * 1.6) * (1 - outP);
  if (hero) {
    const kind = HEROES[Math.floor(random(`hero${c}`) * HEROES.length)];
    const text = chunk.map((w) => w.text).join(" ");
    const size = Math.max(70, Math.min(128, 330 / Math.max(6, text.length) * 11));
    const flick = kind === "fire" ? 1 + (random(`f${frame}`) - 0.5) * 0.04 : 1;
    const style: Record<Hero, React.CSSProperties> = {
      gold: { fontFamily: FONT_SERIF, fontStyle: "italic", fontWeight: 800, background: `linear-gradient(180deg,${THEME.hot} 0%,${THEME.accent} 45%,${THEME.accent2} 100%)`, WebkitBackgroundClip: "text", color: "transparent", filter: "drop-shadow(0 6px 14px rgba(0,0,0,.6))" },
      neon: { fontFamily: SANS, fontWeight: 800, color: THEME.text, textShadow: `0 0 10px ${THEME.accent}, 0 0 28px ${THEME.accent2}, 0 0 60px ${THEME.accent2}`, letterSpacing: 4 },
      fire: { fontFamily: SANS, fontWeight: 900, background: `linear-gradient(180deg,${THEME.text} 0%,${THEME.accent} 55%,${THEME.accent2} 100%)`, WebkitBackgroundClip: "text", color: "transparent", filter: `drop-shadow(0 0 18px ${THEME.glow})` },
    };
    return (
      <Box bottom={bottom}>
        <div style={{ maxWidth: 960, textAlign: "center", opacity, filter: `blur(${blur}px)`, transform: `scale(${(0.86 + 0.14 * Math.min(1, enter)) * flick}) rotate(${kind === "neon" ? -3 : 0}deg)` }}>
          {chunk.map((w, i) => {
            const p = spring({ frame: frame - Math.round(w.start * fps), fps, config: { damping: 12, stiffness: 200, mass: 0.6 } });
            return (
              <span key={i} style={{ display: "inline-block", margin: "0 0.14em", fontSize: size, lineHeight: 1.05, textTransform: upper ? "uppercase" : "none", opacity: Math.min(1, p * 2), transform: `translateY(${(1 - Math.min(1, p)) * 30}px)`, ...style[kind] }}>
                {w.text}
              </span>
            );
          })}
        </div>
      </Box>
    );
  }
  return (
    <Box bottom={bottom}>
      <div style={{ maxWidth: 820, textAlign: "center", fontFamily: SANS, fontWeight: 700, fontSize: 54, lineHeight: 1.25, letterSpacing: 7, textTransform: upper ? "uppercase" : "none", opacity, filter: `blur(${blur}px)`, transform: `translateY(${(1 - Math.min(1, enter)) * 14}px)` }}>
        {chunk.map((w, i) => (
          <span key={i} style={{ display: "inline-block", margin: "0 0.28em", color: THEME.text, opacity: t >= w.start - 0.02 || i <= active ? 1 : 0.42, textShadow: "0 0 18px rgba(255,255,255,.55), 0 4px 14px rgba(0,0,0,.7)" }}>
            {w.text}
          </span>
        ))}
      </div>
    </Box>
  );
};

// ---- karaoke: bold words, the spoken one lights up in the accent colour (no pill) ----
const Karaoke: React.FC<Props> = ({ words, emphasis = [], upper = true, bottom = 400 }) => {
  const s = useChunk(words, 3, 20);
  if (!s) return null;
  const { frame, fps, t, c, chunk, local, outP, active } = s;
  const emph = new Set(emphasis.map(norm));
  const enter = spring({ frame: local, fps, config: { damping: 13, stiffness: 260, mass: 0.55 } });
  return (
    <Box bottom={bottom}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "6px 22px", maxWidth: 940, fontFamily: SANS, fontWeight: 900, fontSize: 92, lineHeight: 1.08, textAlign: "center", textTransform: upper ? "uppercase" : "none", opacity: 1 - outP, transform: `scale(${0.85 + 0.15 * Math.min(1, enter)})` }}>
        {chunk.map((w, i) => {
          const on = i === active && t >= w.start - 0.01;
          const p = spring({ frame: frame - Math.round(w.start * fps), fps, config: { damping: 9, stiffness: 300, mass: 0.5 } });
          const hot = emph.has(norm(w.text)) || /\d/.test(w.text);
          return (
            <span key={`${c}-${i}`} style={{ display: "inline-block", color: on ? (hot ? THEME.hot : THEME.accent) : THEME.text, transform: `scale(${on ? 1 + 0.14 * Math.min(1.3, p) : 1})`, WebkitTextStroke: `10px ${THEME.ink}`, paintOrder: "stroke fill", textShadow: on ? `0 0 34px ${hot ? THEME.hot : THEME.accent}88` : "0 6px 16px rgba(0,0,0,.6)" }}>
              {w.text}
            </span>
          );
        })}
      </div>
    </Box>
  );
};

// ---- stack: one big word at a time, each slams in ----
const Stack: React.FC<Props> = ({ words, emphasis = [], upper = true, bottom = 420 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  let idx = -1;
  for (let i = 0; i < words.length; i++) if (words[i].start - 0.03 <= t) idx = i;
  if (idx < 0) return null;
  const w = words[idx];
  if (t > w.end + 0.35 && idx === words.length - 1) return null;
  const emph = new Set(emphasis.map(norm));
  const hot = emph.has(norm(w.text)) || /\d/.test(w.text);
  const p = spring({ frame: frame - Math.round((w.start - 0.03) * fps), fps, config: { damping: 8, stiffness: 340, mass: 0.5 } });
  const colors = [THEME.text, THEME.accent, THEME.text, THEME.accent2];
  const color = hot ? THEME.hot : colors[idx % colors.length];
  const size = Math.max(90, Math.min(200, 1500 / Math.max(5, w.text.length) * 0.62));
  return (
    <Box bottom={bottom}>
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: size, color, textTransform: upper ? "uppercase" : "none", transform: `scale(${0.5 + 0.5 * Math.min(1.25, p)}) rotate(${hot ? -4 : 0}deg)`, opacity: Math.min(1, p * 3), WebkitTextStroke: `12px ${THEME.ink}`, paintOrder: "stroke fill", textShadow: "0 10px 30px rgba(0,0,0,.6)", textAlign: "center", maxWidth: 980 }}>
        {w.text}
      </div>
    </Box>
  );
};

// ---- typewriter: a dark terminal-ish strip, letters typed at the speed they are spoken ----
const Typewriter: React.FC<Props> = ({ words, upper = false, bottom = 400 }) => {
  const s = useChunk(words, 3, 26, 0.05, 0.4);
  if (!s) return null;
  const { t, chunk, outP } = s;
  let shown = "";
  chunk.forEach((w, i) => {
    const full = w.text + (i < chunk.length - 1 ? " " : "");
    const span = Math.max(0.12, w.end - w.start);
    const frac = Math.min(1, Math.max(0, (t - w.start + 0.02) / (span * 0.9)));
    shown += full.slice(0, Math.ceil(full.length * frac));
  });
  const cursor = Math.floor(t * 2.4) % 2 === 0;
  return (
    <Box bottom={bottom}>
      <div style={{ maxWidth: 940, background: "rgba(6,8,13,0.86)", border: `2px solid ${THEME.cardEdge}`, borderRadius: 22, padding: "22px 34px", fontFamily: MONO, fontWeight: 700, fontSize: 54, lineHeight: 1.3, color: THEME.text, textTransform: upper ? "uppercase" : "none", opacity: 1 - outP, boxShadow: "0 14px 40px rgba(0,0,0,.45)" }}>
        <span style={{ color: THEME.accent }}>{"> "}</span>
        {shown}
        <span style={{ color: THEME.accent, opacity: cursor ? 1 : 0 }}>▌</span>
      </div>
    </Box>
  );
};

// One entry point for the scenes: the style comes from the reel's look (agent/looks.py).
// Smart placement: the scene analysis found the emptiest spot of the picture moment by moment; the captions glide there (0.2 s ease) instead of sitting at a fixed place.
const useZoneShift = (zones?: CaptionZone[]) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!zones || zones.length === 0) return 0;
  const t = frame / fps;
  let k = 0;
  for (let i = 0; i < zones.length; i++) if (zones[i].from <= t) k = i;
  const cur = zones[k].y;
  const prev = k > 0 ? zones[k - 1].y : cur;
  const e = interpolate(t, [zones[k].from, zones[k].from + 0.22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ease = 1 - Math.pow(1 - e, 3);
  return prev + (cur - prev) * ease - DEFAULT_Y;
};

const ALPHA_LANE_SHIFT = -560;      // with the transparent presenter the captions sit in the lane just above his head (their usual place is over his hands)

export const CaptionLayer: React.FC<Props> = (p) => {
  const stage = React.useContext(StageContext);
  const dy = useZoneShift(p.zones) + (stage < 1 ? ALPHA_LANE_SHIFT : 0);
  if (p.style && stage < 1 && !REF_FIXED.has(p.style)) return <AbsoluteFill style={{ zIndex: 30, transform: `translateY(${dy}px)` }}><CaptionStyleSwitch {...p} /></AbsoluteFill>;
  if (p.style && REF_FIXED.has(p.style)) return <AbsoluteFill style={{ zIndex: 30 }}><CaptionStyleSwitch {...p} /></AbsoluteFill>;     // these sit at their own place on the frame
  return (
    <AbsoluteFill style={{ zIndex: 30, transform: dy ? `translateY(${dy}px)` : undefined }}>
      <CaptionStyleSwitch {...p} />
    </AbsoluteFill>
  );
};

const CaptionStyleSwitch: React.FC<Props> = (p) => {
  const Ref = p.style ? REF_CAPTIONS[p.style as string] : undefined;
  if (Ref) return <Ref {...p} />;
  switch (p.style) {
    case "cinematic": return <Cinematic {...p} />;
    case "karaoke": return <Karaoke {...p} />;
    case "stack": return <Stack {...p} />;
    case "typewriter": return <Typewriter {...p} />;
    default: return <Captions words={p.words} emphasis={p.emphasis} upper={p.upper} bottom={p.bottom} accent={THEME.accent} emphasisFrom={THEME.accent2} emphasisTo={THEME.hot} />;
  }
};
