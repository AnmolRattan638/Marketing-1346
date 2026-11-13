// Camera for footage: a list of moves (agent/camera_plan.py) -> one smooth transform. The state is a zoom `s` and a focus point (fx, fy in 0..1 of the frame)
// that is kept at the centre of the screen; translation is clamped so the picture always covers the frame.
export interface CameraMove {
  move: "zoom_in" | "zoom_out" | "pan_down" | "pan_up" | "pan_left" | "pan_right" | "reset";
  atSecond: number;
  seconds: number;
  scale?: number;
  focus?: [number, number];
}

interface State { s: number; fx: number; fy: number }
const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

function target(st: State, m: CameraMove): State {
  const s = m.scale ?? 1.3;
  switch (m.move) {
    case "zoom_in": return { s: Math.max(st.s, s), fx: m.focus?.[0] ?? st.fx, fy: m.focus?.[1] ?? st.fy };
    case "zoom_out":
    case "reset": return { s: 1, fx: 0.5, fy: 0.5 };
    case "pan_down": return { s: Math.max(st.s, s), fx: m.focus?.[0] ?? st.fx, fy: m.focus?.[1] ?? Math.min(0.8, st.fy + 0.3) };
    case "pan_up": return { s: Math.max(st.s, s), fx: m.focus?.[0] ?? st.fx, fy: m.focus?.[1] ?? Math.max(0.2, st.fy - 0.3) };
    case "pan_left": return { s: Math.max(st.s, s), fx: m.focus?.[0] ?? Math.max(0.2, st.fx - 0.25), fy: m.focus?.[1] ?? st.fy };
    case "pan_right": return { s: Math.max(st.s, s), fx: m.focus?.[0] ?? Math.min(0.8, st.fx + 0.25), fy: m.focus?.[1] ?? st.fy };
  }
}

export function cameraAt(moves: CameraMove[], t: number, W = 1080, H = 1920) {
  let st: State = { s: 1, fx: 0.5, fy: 0.5 };
  for (const m of [...moves].sort((a, b) => a.atSecond - b.atSecond)) {
    if (t < m.atSecond) break;
    const to = target(st, m);
    const p = m.seconds <= 0 ? 1 : clamp((t - m.atSecond) / m.seconds, 0, 1);
    const e = ease(p);
    const next = { s: st.s + (to.s - st.s) * e, fx: st.fx + (to.fx - st.fx) * e, fy: st.fy + (to.fy - st.fy) * e };
    if (p < 1) { st = next; break; }
    st = to;
  }
  const lim = (st.s - 1) / 2;
  return {
    scale: st.s,
    x: clamp(-(st.fx - 0.5) * W * st.s, -lim * W, lim * W),
    y: clamp(-(st.fy - 0.5) * H * st.s, -lim * H, lim * H),
  };
}
