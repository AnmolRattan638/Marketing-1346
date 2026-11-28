import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionWord } from "../components/Captions";
import { CaptionLayer, CaptionStyle } from "../components/CaptionStyles";
import { REF_FIXED } from "../components/RefCaptions";
import { FxItem, FxLayer } from "../effects/FxLayer";
import { FilmGrain } from "../effects/FilmGrain";
import { Arrival, arrival } from "../effects/motion";
import { Background } from "../graphics/Background";
import { Heading, StepBadge, Chips } from "../graphics/Heading";
import { StrikeList } from "../graphics/StrikeList";
import { MockHost } from "../graphics/MockHost";
import { LogoOutro } from "../graphics/LogoOutro";
import { CircleWipe } from "../graphics/CircleWipe";
import { ArrivalOverlay, HookTiles, InverseCard, NumeralCard } from "../graphics/RefScenes";
import { ProgressBar } from "../graphics/ProgressBar";
import { THEME, GraphicTimes, MockSpec, LOGO_SAFE_TOP, StageContext, STAGE_ORIGIN_Y } from "../graphics/theme";
import { TemplateStage, TemplateSpec } from "../locomotion/TemplateStage";
import { BeforeAfterBoard, BeforeAfterSpec } from "../graphics/BeforeAfter";
import { BrowserSite, ChatSpec, PhoneChat, SiteSpec } from "../graphics/Devices";
import { HookBlast, HookSpec } from "../graphics/HookBlast";
import { AvatarPanel, AvatarSpec } from "../graphics/AvatarPanel";

export interface GraphicSceneProps {
  layout: "title" | "step" | "strike" | "punch" | "logo" | "tpl" | "ba" | "chat" | "site" | "hook" | "avatar" | "numeral" | "inverse" | "tiles";
  avatar?: AvatarSpec; // layout "avatar": the masked character in the lower screen, heading above (agent/avatar.py)
  hook?: HookSpec; // layout "hook": the breaking-phone opening (agent/scenarios.py HOOK_NOTIFS), hardcoded for scene 1
  chat?: ChatSpec; // layout "chat": a phone with a customer / chatbot conversation (agent/scenarios.py)
  site?: SiteSpec; // layout "site": a browser with a website, a cursor click and an enquiry notification
  ba?: BeforeAfterSpec; // layout "ba": before (no website / no marketing) vs after (website + chatbot), agent/scenarios.py
  tpl?: TemplateSpec; // layout "tpl": one of the imported animation templates (agent/templates.py picks it)
  words: CaptionWord[];
  step?: string;
  kicker?: string;
  heading?: string;
  heading2?: string;
  ghost?: string;
  chips?: string[];
  items?: string[];
  mock?: MockSpec;
  times: GraphicTimes;
  logo?: string;
  cta?: string;
  emphasis?: string[];
  pulses?: number[];
  fx?: FxItem[];
  transitionIn?: Arrival | "circle";
  captionStyle?: CaptionStyle; // from the reel's look (agent/looks.py)
  grain?: number;
  progress?: [number, number];
  showProgress?: boolean;
  fadeOutFrames?: number;
}

// A motion-graphic scene: no footage, the layout draws the picture and every element lands on its spoken word (times come from agent/graphics.py).
// Own palette and own captions; the layouts are inspired by explainer reels (step badge + heading + mock-up card, struck-through list, punch slide).
const GraphicScene: React.FC<GraphicSceneProps> = ({
  layout, tpl, ba, chat, site, hook, avatar, words, step, kicker, heading = "", heading2, ghost, chips = [], items = [], mock, times, logo, cta,
  emphasis = [], pulses = [], fx = [], transitionIn = "settle", captionStyle, grain = 0, progress, showProgress = true, fadeOutFrames = 0,
}) => {
  const stage = React.useContext(StageContext);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const circle = transitionIn === "circle";
  const look = arrival(circle ? "settle" : (transitionIn as Arrival), frame, fps);
  const punch = pulses.reduce((s, p) => {
    const f = frame - Math.round(p * fps);
    return f < 0 || f > 20 ? s : s + 0.03 * (f < 2 ? f / 2 : Math.exp(-(f - 2) / 4));
  }, 0);
  const fadeOut = fadeOutFrames > 0 ? interpolate(frame, [durationInFrames - fadeOutFrames, durationInFrames], [1, 0], { extrapolateLeft: "clamp" }) : 1;
  const isPunch = layout === "punch";
  const isLogo = layout === "logo";

  let body: React.ReactNode = null;
  if (layout === "title") {
    body = (
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px", paddingBottom: 300 }}>
        <Heading kicker={kicker} heading={heading} heading2={heading2} at={times.heading} align="center" size={140} />
        {chips.length ? <div style={{ marginTop: 60 }}><Chips items={chips} at={times.chips} align="center" /></div> : null}
      </AbsoluteFill>
    );
  } else if (layout === "step") {
    body = (
      <>
        <div style={{ position: "absolute", left: 80, top: LOGO_SAFE_TOP }}>{step ? <StepBadge text={step} at={Math.max(0, times.heading - 0.1)} /> : null}</div>
        <div style={{ position: "absolute", left: 80, right: 80, top: LOGO_SAFE_TOP + 70 }}>
          <Heading kicker={kicker} heading={heading} heading2={heading2} at={times.heading} size={112} />
        </div>
        {mock ? (
          <div style={{ position: "absolute", left: 80, top: 700, width: 920 }}>
            <MockHost mock={mock} at={times.mock} times={times.items} />
          </div>
        ) : null}
      </>
    );
  } else if (layout === "strike") {
    body = (
      <>
        <div style={{ position: "absolute", left: 80, right: 80, top: LOGO_SAFE_TOP }}>
          {kicker ? <div style={{ fontFamily: '"Playfair Display", Georgia, serif', fontStyle: "italic", fontSize: 54, color: THEME.muted, marginBottom: 24 }}>{kicker}</div> : null}
          <StrikeList items={items} times={times.items} />
        </div>
        {heading ? (
          <div style={{ position: "absolute", left: 80, right: 80, top: 1000 }}>
            <Heading heading={heading} heading2={heading2} at={times.heading} size={104} />
          </div>
        ) : null}
      </>
    );
  } else if (isPunch) {
    body = (
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 70px", paddingBottom: 320 }}>
        <Heading kicker={kicker} heading={heading} heading2={heading2} at={times.heading} align="center" size={150} accent={THEME.ink} second={THEME.bgBottom} />
        {chips.length ? <div style={{ marginTop: 60 }}><Chips items={chips} at={times.chips} align="center" /></div> : null}
      </AbsoluteFill>
    );
  } else if (layout === "avatar" && avatar) {
    body = (
      <>
        <AvatarPanel spec={avatar} />
        <div style={{ position: "absolute", left: 70, right: 70, top: LOGO_SAFE_TOP + 40 }}>
          <Heading kicker={kicker} heading={heading} heading2={heading2} at={times.heading} align="center" size={118} />
        </div>
        {chips.length ? <div style={{ position: "absolute", left: 70, right: 70, top: LOGO_SAFE_TOP + 560 }}><Chips items={chips} at={times.chips} align="center" /></div> : null}
      </>
    );
  } else if (layout === "numeral") {
    body = <NumeralCard numeral={step || "1"} title={heading} line={kicker} at={Math.max(0.2, times.heading)} />;
  } else if (layout === "inverse") {
    body = <InverseCard text={heading} at={Math.max(0.1, times.heading)} />;
  } else if (layout === "tiles") {
    body = <HookTiles title={heading} sub={kicker} tiles={items} times={times.items} />;
  } else if (layout === "hook") {
    body = <HookBlast words={words} emphasis={emphasis as any} spec={hook} duration={durationInFrames / fps} />;
  } else if (layout === "chat" && chat) {
    body = <PhoneChat spec={chat} at={Math.max(0.2, times.heading)} />;
  } else if (layout === "site" && site) {
    body = <BrowserSite spec={site} at={Math.max(0.2, times.heading)} />;
  } else if (layout === "ba" && ba) {
    body = <BeforeAfterBoard spec={ba} at={Math.max(0.2, times.heading)} />;
  } else if (layout === "tpl" && tpl) {
    body = <TemplateStage {...tpl} />;
  } else if (isLogo) {
    body = <LogoOutro logo={logo} cta={cta} />;
  }

  return (
    <AbsoluteFill style={{ backgroundColor: THEME.bgTop, opacity: fadeOut }}>
      <AbsoluteFill
        style={{
          transform: `translate(${look.translateX}px, ${look.translateY}px) scale(${(1 + punch) * look.scale})`,
          filter: look.blur || look.hue || look.brightness !== 1 ? `blur(${look.blur}px) hue-rotate(${look.hue}deg) brightness(${look.brightness})` : undefined,
          opacity: look.opacity,
          clipPath: look.clip,
        }}
      >
        <Background punch={isPunch} ghost={isPunch ? ghost || heading.split(" ")[0] : undefined} />
        {stage < 1 && !isLogo ? <AbsoluteFill style={{ transform: `scale(${stage})`, transformOrigin: `50% ${STAGE_ORIGIN_Y}px` }}>{body}</AbsoluteFill> : body}
      </AbsoluteFill>
      <FxLayer items={fx} />
      {isLogo || layout === "hook" || layout === "inverse" ? null : <div style={{ position: "absolute", inset: 0, ...(captionStyle === "explode" && stage >= 1 ? { transform: "translateY(480px)" } : {}) }}><CaptionLayer words={words} emphasis={emphasis} upper style={captionStyle && REF_FIXED.has(captionStyle) && captionStyle !== "explode" ? undefined : captionStyle} /></div>}   {/* the placed reference styles are for footage scenes: a card with its own heading keeps the bottom pill; the inverse card already carries the words */}
      {grain > 0 ? <FilmGrain opacity={grain} /> : null}
      {showProgress && progress && !isLogo ? <ProgressBar progress={progress} light={isPunch} /> : null}
      {circle ? <CircleWipe /> : null}
      {transitionIn === "sweep" || transitionIn === "leak" ? <ArrivalOverlay kind={transitionIn} /> : null}
    </AbsoluteFill>
  );
};

export default GraphicScene;
