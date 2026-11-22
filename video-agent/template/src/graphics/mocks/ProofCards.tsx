import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { fade, pop } from "../anim";
import { FONT_HEAD, THEME } from "../theme";
import { WindowCard } from "./WindowCard";

// Proof cards: a picture of the problem instead of a stock photo. They only ever show a SCENE (a message waiting, a listing, a slow gauge), never a real result,
// so each carries an "Example" tag and uses no figures. Brand palette only.
const ExampleTag: React.FC<{ at: number }> = ({ at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{ position: "absolute", top: -62, right: 0, fontSize: 24, fontWeight: 700, letterSpacing: 2, color: THEME.muted, opacity: fade(frame, fps, at + 0.2, 0.4) }}>EXAMPLE</div>
  );
};

// A chat: each item is a bubble. "you:" starts the business's reply (right, gold); anything else is the customer (left). "..." as the last item shows an unanswered state.
export const ChatCard: React.FC<{ at: number; title?: string; items: string[]; times: number[] }> = ({ at, title, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <WindowCard at={at} height={760} title={title || "WhatsApp"}>
      <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 22, marginTop: 8 }}>
        <ExampleTag at={at} />
        {items.map((raw, i) => {
          const mine = /^you:/i.test(raw);
          const waiting = raw.trim() === "...";
          const text = raw.replace(/^you:\s*/i, "");
          const p = pop(frame, fps, times[i] ?? at + 0.5 + i * 0.9, { damping: 14, stiffness: 200, mass: 0.7 });
          return (
            <div key={i} style={{ alignSelf: mine ? "flex-end" : "flex-start", maxWidth: "82%", opacity: Math.min(1, p * 2), transform: `translateY(${(1 - p) * 30}px) scale(${0.9 + 0.1 * p})` }}>
              <div style={{ background: mine ? THEME.accent : "rgba(255,255,255,0.1)", color: mine ? THEME.ink : THEME.text, fontSize: 40, fontWeight: 600, lineHeight: 1.25, padding: "20px 28px", borderRadius: 30, borderBottomRightRadius: mine ? 8 : 30, borderBottomLeftRadius: mine ? 30 : 8 }}>
                {waiting ? <span style={{ letterSpacing: 8, color: THEME.muted }}>●●●</span> : text}
              </div>
            </div>
          );
        })}
      </div>
    </WindowCard>
  );
};

// A map listing: [name, category, status line]. Four stars are drawn but no rating number or review count (those would be figures).
export const MapsCard: React.FC<{ at: number; items: string[]; times: number[] }> = ({ at, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [name = "Your Business", category = "", status = ""] = items;
  const a = pop(frame, fps, times[0] ?? at + 0.4, { damping: 15, stiffness: 190, mass: 0.7 });
  const b = pop(frame, fps, times[1] ?? at + 1.0, { damping: 16, stiffness: 170, mass: 0.8 });
  const c = pop(frame, fps, times[2] ?? at + 1.6, { damping: 12, stiffness: 240, mass: 0.7 });
  return (
    <WindowCard at={at} height={700} title="Google Maps">
      <div style={{ position: "relative" }}>
        <ExampleTag at={at} />
        <div style={{ height: 250, borderRadius: 26, background: `linear-gradient(140deg, ${THEME.card}, ${THEME.cardEdge})`, position: "relative", overflow: "hidden", marginTop: 6 }}>
          {[0.18, 0.42, 0.66, 0.84].map((x) => (
            <div key={x} style={{ position: "absolute", left: `${x * 100}%`, top: 0, bottom: 0, width: 3, background: "rgba(255,255,255,0.07)" }} />
          ))}
          {[0.25, 0.55, 0.8].map((y) => (
            <div key={y} style={{ position: "absolute", top: `${y * 100}%`, left: 0, right: 0, height: 3, background: "rgba(255,255,255,0.07)" }} />
          ))}
          <div style={{ position: "absolute", left: "50%", top: "46%", width: 46, height: 46, marginLeft: -23, marginTop: -46, borderRadius: "50% 50% 50% 0", transform: `rotate(-45deg) scale(${0.3 + 0.7 * a})`, background: THEME.accent, boxShadow: `0 0 40px ${THEME.glow}` }} />
        </div>
        <div style={{ marginTop: 26, fontFamily: FONT_HEAD, opacity: Math.min(1, a * 2), transform: `translateY(${(1 - a) * 24}px)` }}>
          <div style={{ fontSize: 58, fontWeight: 900, lineHeight: 1.05 }}>{name}</div>
          <div style={{ fontSize: 34, color: THEME.accent, marginTop: 12, letterSpacing: 4, opacity: Math.min(1, b * 2) }}>★★★★☆</div>
          <div style={{ fontSize: 34, color: THEME.muted, marginTop: 10, opacity: Math.min(1, b * 2) }}>{category}</div>
          {status ? <div style={{ display: "inline-block", marginTop: 20, fontSize: 34, fontWeight: 800, color: THEME.ink, background: THEME.hot, padding: "10px 26px", borderRadius: 30, transform: `scale(${0.5 + 0.5 * c})`, opacity: Math.min(1, c * 2), transformOrigin: "left center" }}>{status}</div> : null}
        </div>
      </div>
    </WindowCard>
  );
};

// A speed gauge with no number: [label, verdict, zone]. The needle swings into zone "slow" (left), "ok" (middle) or "fast" (right).
export const GaugeCard: React.FC<{ at: number; items: string[]; times: number[] }> = ({ at, items, times }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [label = "Mobile speed", verdict = "Slow", zone = "slow"] = items;
  const target = zone === "fast" ? 62 : zone === "ok" ? 0 : -62;
  const p = pop(frame, fps, times[0] ?? at + 0.6, { damping: 12, stiffness: 90, mass: 1.1 });
  const v = pop(frame, fps, times[1] ?? at + 1.6, { damping: 12, stiffness: 240, mass: 0.7 });
  const R = 250;
  const arc = (from: number, to: number) => {
    const pt = (deg: number) => [R + R * 0.86 * Math.cos(((deg - 180) * Math.PI) / 180), R + R * 0.86 * Math.sin(((deg - 180) * Math.PI) / 180)];
    const [x1, y1] = pt(from);
    const [x2, y2] = pt(to);
    return `M ${x1} ${y1} A ${R * 0.86} ${R * 0.86} 0 0 1 ${x2} ${y2}`;
  };
  return (
    <WindowCard at={at} height={700} title={label}>
      <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <ExampleTag at={at} />
        <svg width={R * 2} height={R + 30} viewBox={`0 0 ${R * 2} ${R + 30}`} style={{ marginTop: 20 }}>
          <path d={arc(0, 58)} stroke={THEME.cardEdge} strokeWidth={46} fill="none" strokeLinecap="round" />
          <path d={arc(62, 118)} stroke="rgba(255,255,255,0.18)" strokeWidth={46} fill="none" strokeLinecap="round" />
          <path d={arc(122, 180)} stroke={THEME.accent2} strokeWidth={46} fill="none" strokeLinecap="round" />
          <g transform={`translate(${R} ${R}) rotate(${target * p})`}>
            <rect x={-8} y={-R * 0.78} width={16} height={R * 0.78} rx={8} fill={THEME.accent} />
          </g>
          <circle cx={R} cy={R} r={26} fill={THEME.accent} />
        </svg>
        <div style={{ marginTop: 22, fontFamily: FONT_HEAD, fontSize: 84, fontWeight: 900, color: THEME.hot, transform: `scale(${0.5 + 0.5 * v})`, opacity: Math.min(1, v * 2) }}>{verdict}</div>
      </div>
    </WindowCard>
  );
};
