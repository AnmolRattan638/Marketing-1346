import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_HEAD, LOGO_SAFE_TOP, THEME } from "./theme";
import { fade, pop } from "./anim";

// Device scenes for the website / chatbot services. Frames and cursor are adapted in spirit from remotion-saas-showcase (MIT, Jason Lin), rewritten with inline
// styles and the reel's theme colours. Copy is generic and illustrative (agent/scenarios.py); nothing shows a real client, price or result.

export interface ChatSpec {
  title: string;
  messages: { from: "customer" | "bot"; text: string }[];
}
export interface SiteSpec {
  url: string;
  headline: string;
  sub: string;
  button: string;
  toast: string;
}

const Dots: React.FC<{ frame: number }> = ({ frame }) => (
  <div style={{ display: "flex", gap: 8, padding: "6px 4px" }}>
    {[0, 1, 2].map((i) => (
      <div key={i} style={{ width: 14, height: 14, borderRadius: 7, background: THEME.muted, opacity: 0.4 + 0.6 * Math.abs(Math.sin((frame + i * 5) / 6)) }} />
    ))}
  </div>
);

export const PhoneChat: React.FC<{ spec: ChatSpec; at: number }> = ({ spec, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = pop(frame, fps, at);
  // each message lands 1.5 s after the previous; a bot reply is preceded by 0.9 s of typing dots
  let t = at + 0.5;
  const rows = spec.messages.map((m) => {
    const typingFrom = m.from === "bot" ? t : null;
    const shows = m.from === "bot" ? t + 0.9 : t;
    t = shows + 1.5;
    return { m, typingFrom, shows };
  });
  const S = 1.5;
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: LOGO_SAFE_TOP - 10 }}>
      <div style={{ width: 390 * S, height: 700 * S, borderRadius: 52 * S / 1.5, background: THEME.bgBottom, border: `${5}px solid ${THEME.cardEdge}`, boxShadow: `0 30px 90px rgba(0,0,0,0.5), 0 0 80px ${THEME.glowSoft}`, overflow: "hidden", opacity: Math.min(1, enter), transform: `translateY(${(1 - Math.min(1, enter)) * 60}px)`, boxSizing: "border-box" }}>
        <div style={{ height: 46, display: "flex", justifyContent: "center", alignItems: "center" }}><div style={{ width: 150, height: 26, borderRadius: 13, background: "#000" }} /></div>
        <div style={{ padding: "14px 26px", background: THEME.card, borderBottom: `2px solid ${THEME.cardEdge}`, display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 58, height: 58, borderRadius: 29, background: THEME.accent, color: THEME.ink, fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 30, display: "flex", alignItems: "center", justifyContent: "center" }}>{spec.title.slice(0, 1).toUpperCase()}</div>
          <div>
            <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 30, color: THEME.text }}>{spec.title}</div>
            <div style={{ fontFamily: FONT_HEAD, fontWeight: 600, fontSize: 22, color: THEME.accent }}>online</div>
          </div>
        </div>
        <div style={{ padding: "24px 22px", display: "flex", flexDirection: "column", gap: 18 }}>
          {rows.map(({ m, typingFrom, shows }, i) => {
            const p = pop(frame, fps, shows);
            const typing = typingFrom !== null && frame / fps >= typingFrom && frame / fps < shows;
            const bot = m.from === "bot";
            if (typing) return <div key={i} style={{ alignSelf: "flex-start", background: THEME.card, border: `2px solid ${THEME.cardEdge}`, borderRadius: 26, padding: "10px 18px" }}><Dots frame={frame} /></div>;
            if (frame / fps < shows) return null;
            return (
              <div key={i} style={{ alignSelf: bot ? "flex-start" : "flex-end", maxWidth: "82%", padding: "16px 22px", borderRadius: 28, borderBottomLeftRadius: bot ? 6 : 28, borderBottomRightRadius: bot ? 28 : 6, background: bot ? THEME.card : THEME.accent, border: bot ? `2px solid ${THEME.cardEdge}` : "none", color: bot ? THEME.text : THEME.bgTop, fontFamily: FONT_HEAD, fontWeight: 600, fontSize: 31, lineHeight: "40px", opacity: Math.min(1, p), transform: `scale(${0.9 + 0.1 * Math.min(1, p)})`, transformOrigin: bot ? "left bottom" : "right bottom" }}>{m.text}</div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Cursor: React.FC<{ x: number; y: number; click: number }> = ({ x, y, click }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: `scale(${1 - 0.18 * click})`, transformOrigin: "top left", filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.5))" }}>
    <svg width="54" height="54" viewBox="0 0 24 24"><path d="M4 2l16 9-7 2-3 7z" fill={THEME.text} stroke={THEME.ink} strokeWidth="1.4" strokeLinejoin="round" /></svg>
  </div>
);

export const BrowserSite: React.FC<{ spec: SiteSpec; at: number }> = ({ spec, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = pop(frame, fps, at);
  const t = frame / fps;
  const tMove = at + 0.9, tClick = at + 2.0, tToast = at + 2.3;
  const k = Math.min(1, Math.max(0, (t - tMove) / (tClick - tMove)));
  const ease = k * k * (3 - 2 * k);
  const W = 940, H = 700;
  const cx = 700 + (245 - 700) * ease - 9, cy = 640 + (462 - 640) * ease - 5;        // the cursor tip travels onto the button

  const click = t >= tClick && t < tClick + 0.25 ? 1 : 0;
  const toast = pop(frame, fps, tToast);
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: LOGO_SAFE_TOP + 40 }}>
      <div style={{ position: "relative", width: W, height: H, borderRadius: 30, overflow: "hidden", background: THEME.card, border: `4px solid ${THEME.cardEdge}`, boxShadow: `0 30px 90px rgba(0,0,0,0.5), 0 0 80px ${THEME.glowSoft}`, opacity: Math.min(1, enter), transform: `translateY(${(1 - Math.min(1, enter)) * 60}px)` }}>
        <div style={{ height: 76, display: "flex", alignItems: "center", gap: 14, padding: "0 24px", background: THEME.bgBottom, borderBottom: `2px solid ${THEME.cardEdge}` }}>
          {[THEME.muted, THEME.muted, THEME.muted].map((c, i) => <div key={i} style={{ width: 18, height: 18, borderRadius: 9, background: c, opacity: 0.5 }} />)}
          <div style={{ flex: 1, marginLeft: 16, height: 42, borderRadius: 21, background: THEME.card, display: "flex", alignItems: "center", padding: "0 20px", fontFamily: FONT_HEAD, fontWeight: 600, fontSize: 26, color: THEME.muted }}>{spec.url}</div>
        </div>
        <div style={{ padding: "70px 60px" }}>
          <div style={{ fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 62, lineHeight: "70px", color: THEME.text, opacity: fade(frame, fps, at + 0.2) }}>{spec.headline}</div>
          <div style={{ marginTop: 22, fontFamily: FONT_HEAD, fontWeight: 600, fontSize: 32, lineHeight: "42px", color: THEME.muted, opacity: fade(frame, fps, at + 0.45) }}>{spec.sub}</div>
          <div style={{ marginTop: 50, display: "inline-block", padding: "22px 46px", borderRadius: 18, background: THEME.accent, color: THEME.ink, fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 36, opacity: fade(frame, fps, at + 0.6), transform: `scale(${click ? 0.95 : 1})`, boxShadow: `0 0 ${click ? 50 : 24}px ${THEME.glow}` }}>{spec.button}</div>
        </div>
        <Cursor x={cx} y={cy} click={click} />
        <div style={{ position: "absolute", right: 30, bottom: 36, padding: "20px 28px", borderRadius: 20, background: THEME.bgBottom, border: `3px solid ${THEME.accent}`, color: THEME.text, fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 30, opacity: Math.min(1, toast), transform: `translateY(${(1 - Math.min(1, toast)) * 30}px)`, boxShadow: `0 0 40px ${THEME.glowSoft}` }}>{"✓ "}{spec.toast}</div>
      </div>
    </AbsoluteFill>
  );
};
