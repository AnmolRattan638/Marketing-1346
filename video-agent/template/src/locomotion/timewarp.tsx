import React, { createContext, useContext } from "react";
import { useCurrentFrame as useRemotionFrame } from "remotion";

// The templates read their frame from here, so TemplateStage can bend time: a template moment (frame 22 = "bottom text lands") is pinned to a scene moment (the spoken word).
export type Warp = (sceneFrame: number) => number;
export const WarpContext = createContext<Warp | null>(null);

export const useCurrentFrame = (): number => {
  const f = useRemotionFrame();
  const w = useContext(WarpContext);
  return w ? w(f) : f;
};

// anchors: [sceneFrame, templateFrame] pairs, increasing in both. Between two anchors time is stretched linearly; outside them it runs at normal speed.
export const makeWarp = (anchors: [number, number][]): Warp => {
  const a = [...anchors].sort((x, y) => x[0] - y[0]);
  if (!a.length) return (f) => f;
  return (f) => {
    if (f <= a[0][0]) return a[0][1] + (f - a[0][0]);
    for (let i = 1; i < a.length; i++) {
      if (f <= a[i][0]) {
        const [s0, t0] = a[i - 1];
        const [s1, t1] = a[i];
        return t0 + ((f - s0) * (t1 - t0)) / Math.max(1, s1 - s0);
      }
    }
    const [sl, tl] = a[a.length - 1];
    return tl + (f - sl);
  };
};
