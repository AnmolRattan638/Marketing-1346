import { spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export interface FrameSpringOptions {
  from?: number;          // start value
  to?: number;            // end value
  delay?: number;         // frames before spring starts
  damping?: number;       // Remotion spring damping (default 20)
  mass?: number;          // Remotion spring mass (default 1)
  stiffness?: number;     // Remotion spring stiffness (default 100)
}

// Wraps Remotion's spring() with sensible motion-design defaults and an
// interpolate() on top so callers get a 0→1 progress value remapped to
// [from, to]. Use this for any single-axis animation (opacity, scale, x, y).
export function useFrameSpring(opts: FrameSpringOptions = {}): number {
  const {
    from = 0,
    to = 1,
    delay = 0,
    damping = 20,
    mass = 1,
    stiffness = 100,
  } = opts;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    fps,
    frame: Math.max(0, frame - delay),
    config: { damping, mass, stiffness },
  });

  return interpolate(progress, [0, 1], [from, to]);
}
