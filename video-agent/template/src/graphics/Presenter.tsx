import React, { useMemo } from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { THEME } from "./theme";

export interface PresenterSpec {
  src: string[];                       // the poses (agent/avatar.py stages them)
  energy: number[];                    // voice loudness 0..1 for EVERY frame of the whole reel
  cuts: { f: number; i: number }[];    // from frame f the pose is src[i] (a new pose on every scene and every few seconds, like a camera cut)
  hide: [number, number][];            // frame ranges where the character is not drawn (the hook, the big avatar scenes, the logo end)
}

const SIZE = 300;                      // px, the round presenter window; bottom-left, under the captions and clear of the Reels buttons on the right

// The masked presenter, on screen the whole reel. The mouth is covered so nothing needs lip-sync: the voice shows as a nod when a sentence starts, a lift and swell
// while he speaks, a glow ring that follows the loudness, and a slow breathing sway when he is quiet. The pose changes at every scene and every few seconds.
export const Presenter: React.FC<{ spec: PresenterSpec }> = ({ spec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const e = (i: number) => spec.energy[Math.max(0, Math.min(spec.energy.length - 1, i))] ?? 0;
  const loud = (e(frame - 2) + e(frame - 1) + e(frame) + e(frame + 1) + e(frame + 2)) / 5;

  // a sentence starting after a pause = a small nod
  const onsets = useMemo(() => {
    const out: number[] = [];
    for (let i = 8; i < spec.energy.length; i++) {
      const before = (spec.energy[i - 8] + spec.energy[i - 6] + spec.energy[i - 4] + spec.energy[i - 2]) / 4;
      if (before < 0.12 && spec.energy[i] > 0.35 && (!out.length || i - out[out.length - 1] > 12)) out.push(i);
    }
    return out;
  }, [spec.energy]);
  const last = onsets.filter((o) => o <= frame).pop();
  const x = last == null ? 9 : (frame - last) / 9;
  const nod = x >= 1 ? 0 : Math.sin(Math.PI * x) * 12;

  const range = spec.hide.find(([a, b]) => frame >= a - 6 && frame < b + 6);
  const shown = !range;
  const hiddenFade = range ? interpolate(frame, [range[0] - 6, range[0]], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  const lastHideEnd = spec.hide.filter(([, b]) => b <= frame).map(([, b]) => b).pop() ?? 0;
  const pop = spring({ frame: frame - lastHideEnd, fps, config: { damping: 11, stiffness: 140 } });
  if (!shown && hiddenFade <= 0) return null;

  let cur = 0;
  let curFrom = 0;
  for (const c of spec.cuts) if (c.f <= frame) { cur = c.i; curFrom = c.f; }
  const prevCut = spec.cuts.filter((c) => c.f < curFrom).pop();
  const fade = interpolate(frame, [curFrom, curFrom + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const breathe = 1 + 0.012 * Math.sin(t * 1.9);
  const scale = breathe + 0.035 * loud + (nod ? 0.012 : 0);
  const rot = 2.4 * Math.sin(t * 0.9) + 1.2 * Math.sin(t * 2.3 + 1) + loud * 1.4 * Math.sin(t * 9);
  const dx = 7 * Math.sin(t * 1.1);
  const dy = 4 * Math.sin(t * 1.7) - loud * 9 + nod;
  const ring = 0.35 + 0.65 * loud;
  const imgW = SIZE * 1.12;
  const img = (src: string, opacity: number) => (
    <Img src={staticFile(src)} style={{ position: "absolute", width: imgW, height: imgW * (1250 / 1050), left: SIZE / 2 - imgW / 2 + dx * 0.8, top: SIZE / 2 - imgW * (1250 / 1050) * 0.36 + dy * 0.6, opacity }} />
  );
  return (
    <AbsoluteFill style={{ opacity: shown ? 1 : hiddenFade, pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute", left: 36, bottom: 85, width: SIZE, height: SIZE, borderRadius: "50%", overflow: "hidden", background: THEME.bgTop,
          transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg) scale(${scale * (0.55 + 0.45 * Math.min(1, pop))})`,
          border: `6px solid ${THEME.accent}`, boxShadow: `0 0 ${24 + 46 * ring}px ${6 + 12 * ring}px rgba(255,255,255,${0.10 + 0.20 * ring}), 0 10px 40px rgba(0,0,0,0.55)`,
        }}
      >
        {prevCut && fade < 1 ? img(spec.src[prevCut.i] ?? spec.src[0], 1) : null}
        {img(spec.src[cur] ?? spec.src[0], fade)}
      </div>
    </AbsoluteFill>
  );
};
