import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { THEME } from "./theme";

export interface AvatarSpec {
  src: string[];        // one or two poses; with two, the second fades in at swapAt seconds
  energy: number[];     // voice loudness 0..1 per frame of this scene (agent/avatar.py)
  swapAt?: number;
}

// The masked character, lower screen. Nothing here needs lip-sync: the mouth is covered, so the voice is shown by a breathing body,
// a push-in, and a glow behind the head that swells with the loudness of the narration.
export const AvatarPanel: React.FC<{ spec: AvatarSpec }> = ({ spec }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width } = useVideoConfig();
  const t = frame / fps;
  const e = (i: number) => spec.energy[Math.max(0, Math.min(spec.energy.length - 1, i))] ?? 0;
  const loud = (e(frame - 2) + e(frame - 1) + e(frame) + e(frame + 1) + e(frame + 2)) / 5;     // smoothed
  const push = interpolate(frame, [0, durationInFrames], [1.0, 1.07], { extrapolateRight: "clamp" });
  const scale = push + 0.012 * Math.sin(t * 1.7) + 0.035 * loud;
  const lift = Math.sin(t * 1.7) * 7 - loud * 10;
  const rise = interpolate(frame, [0, 14], [90, 0], { extrapolateRight: "clamp" });
  const appear = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const second = spec.src[1] && spec.swapAt != null ? interpolate(t, [spec.swapAt, spec.swapAt + 0.18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const panelW = Math.round(width * 0.96);
  const panelH = Math.round(panelW * (1250 / 1050));
  const img = (src: string, opacity: number) => (
    <Img src={staticFile(src)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity }} />
  );
  return (
    <AbsoluteFill style={{ opacity: appear }}>
      <div style={{ position: "absolute", left: "50%", bottom: 120, width: panelW * 0.9, height: panelW * 0.9, marginLeft: -(panelW * 0.9) / 2, borderRadius: "50%",
        background: `radial-gradient(circle, ${THEME.accent} 0%, transparent 62%)`, opacity: 0.16 + 0.55 * loud, filter: "blur(40px)" }} />
      <div
        style={{
          position: "absolute", left: "50%", bottom: -40, width: panelW, height: panelH, marginLeft: -panelW / 2,
          transform: `translateY(${rise + lift}px) scale(${scale})`, transformOrigin: "50% 80%",
          WebkitMaskImage: "radial-gradient(ellipse 64% 52% at 50% 54%, #000 45%, transparent 100%)",
          maskImage: "radial-gradient(ellipse 64% 52% at 50% 54%, #000 45%, transparent 100%)",
        }}
      >
        {img(spec.src[0], 1 - second)}
        {spec.src[1] ? img(spec.src[1], second) : null}
      </div>
    </AbsoluteFill>
  );
};
