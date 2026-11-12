import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionWord } from "../components/Captions";
import { CaptionLayer, CaptionStyle } from "../components/CaptionStyles";
import { FxItem, FxLayer } from "../effects/FxLayer";
import { FilmGrain } from "../effects/FilmGrain";
import { Arrival, arrival } from "../effects/motion";
import { Background } from "../graphics/Background";
import { Heading, StepBadge, Chips } from "../graphics/Heading";
import { StrikeList } from "../graphics/StrikeList";
import { MockHost } from "../graphics/MockHost";
import { LogoOutro } from "../graphics/LogoOutro";
import { CircleWipe } from "../graphics/CircleWipe";
import { ProgressBar } from "../graphics/ProgressBar";
import { THEME, GraphicTimes, MockSpec } from "../graphics/theme";

export interface GraphicSceneProps {
  layout: "title" | "step" | "strike" | "punch" | "logo";
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
  layout, words, step, kicker, heading = "", heading2, ghost, chips = [], items = [], mock, times, logo, cta,
  emphasis = [], pulses = [], fx = [], transitionIn = "settle", captionStyle, grain = 0, progress, showProgress = true, fadeOutFrames = 0,
}) => {
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
        <div style={{ position: "absolute", left: 80, top: 210 }}>{step ? <StepBadge text={step} at={Math.max(0, times.heading - 0.1)} /> : null}</div>
        <div style={{ position: "absolute", left: 80, right: 80, top: 300 }}>
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
        <div style={{ position: "absolute", left: 80, right: 80, top: 230 }}>
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
        <Heading kicker={kicker} heading={heading} heading2={heading2} at={times.heading} align="center" size={150} accent="#fff" second={THEME.ink} />
        {chips.length ? <div style={{ marginTop: 60 }}><Chips items={chips} at={times.chips} align="center" /></div> : null}
      </AbsoluteFill>
    );
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
        {body}
      </AbsoluteFill>
      <FxLayer items={fx} />
      {isLogo ? null : <CaptionLayer words={words} emphasis={emphasis} upper style={captionStyle} />}
      {grain > 0 ? <FilmGrain opacity={grain} /> : null}
      {showProgress && progress && !isLogo ? <ProgressBar progress={progress} light={isPunch} /> : null}
      {circle ? <CircleWipe /> : null}
    </AbsoluteFill>
  );
};

export default GraphicScene;
