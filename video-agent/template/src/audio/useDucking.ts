// Ducking: return a (frame) => volume function that drops to duckTo during
// narration ranges and rises to baseVolume outside. A short linear ramp at
// each range boundary avoids audible clicks.

export interface NarrationRange {
  startFrame: number;
  endFrame: number; // exclusive
}

export interface DuckingOptions {
  ranges: NarrationRange[];
  baseVolume: number;
  duckTo: number;
  rampFrames?: number; // default 8
}

export function makeDuckingVolume(opts: DuckingOptions): (frame: number) => number {
  const { ranges, baseVolume, duckTo, rampFrames = 8 } = opts;

  return (frame: number): number => {
    // Find the closest range and compute a blend factor 0..1 where 1 = fully ducked.
    let ducked = 0;
    for (const r of ranges) {
      // Inside range
      if (frame >= r.startFrame && frame < r.endFrame) {
        ducked = 1;
        break;
      }
      // Ramp in: rampFrames before startFrame
      if (frame >= r.startFrame - rampFrames && frame < r.startFrame) {
        const t = (frame - (r.startFrame - rampFrames)) / rampFrames;
        ducked = Math.max(ducked, t);
      }
      // Ramp out: rampFrames after endFrame
      if (frame >= r.endFrame && frame < r.endFrame + rampFrames) {
        const t = 1 - (frame - r.endFrame) / rampFrames;
        ducked = Math.max(ducked, t);
      }
    }
    return baseVolume + (duckTo - baseVolume) * ducked;
  };
}
