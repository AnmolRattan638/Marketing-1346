import React from "react";
import { Sequence, useVideoConfig } from "remotion";
import { StatCounter } from "./StatCounter";
import { GlitchText } from "./GlitchText";
import { PopTitle } from "./PopTitle";
import { LowerThird } from "./LowerThird";

export interface FxItem {
  type: "stat" | "glitch" | "title" | "lower_third" | "shake";
  atSecond: number; // from the scene start (the start of the spoken word it belongs to)
  seconds: number;
  text?: string;
  label?: string;
  value?: number;
  prefix?: string;
  suffix?: string;
}

// The graphics of one scene. Each one lives in its own <Sequence>, so its animation starts exactly on its word.
// (Shakes act on the footage, see motion.ts, and are skipped here.)
export const FxLayer: React.FC<{ items: FxItem[] }> = ({ items }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {items
        .filter((it) => it.type !== "shake")
        .map((it, i) => (
          <Sequence key={`${it.type}-${i}`} from={Math.round(it.atSecond * fps)} durationInFrames={Math.max(1, Math.round(it.seconds * fps))}>
            {it.type === "stat" && typeof it.value === "number" ? (
              <StatCounter value={it.value} prefix={it.prefix} suffix={it.suffix} label={it.label ?? it.text} />
            ) : null}
            {it.type === "glitch" && it.text ? <GlitchText text={it.text} /> : null}
            {it.type === "title" && it.text ? <PopTitle text={it.text} label={it.label} /> : null}
            {it.type === "lower_third" && it.text ? <LowerThird text={it.text} label={it.label} /> : null}
          </Sequence>
        ))}
    </>
  );
};
