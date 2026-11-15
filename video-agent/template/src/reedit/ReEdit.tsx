import React from "react";
import { AbsoluteFill, Easing, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { FxLayer, FxItem } from "../effects/FxLayer";
import { LOGO_SAFE_TOP } from "../graphics/theme";
import { ProcedureCard, ProcStep } from "./ProcedureCard";

export interface Zoom { from: number; to: number; scale: number; x: number; y: number }
export interface ProcedureOverlay { type: "procedure"; from: number; to: number; title?: string; position: "top" | "middle" | "bottom"; steps: ProcStep[] }
export type FxOverlay = FxItem; // type stat | glitch | title | lower_third, atSecond, seconds
export interface ReEditProps {
  video: string; // file under public/
  seconds: number;
  zooms: Zoom[];
  procedures: ProcedureOverlay[];
  fx: FxOverlay[];
}

export const reeditDefaults: ReEditProps = { video: "reedit/base.mp4", seconds: 10, zooms: [], procedures: [], fx: [] };

const TOP = { top: LOGO_SAFE_TOP + 20, middle: 700, bottom: 1060 };

// The user's finished clip is the base layer with its own audio. Zooms push in on it; step graphics and effects are laid on top. Nothing is drawn in the logo corner.
export const ReEdit: React.FC<ReEditProps> = ({ video, zooms, procedures, fx }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  let scale = 1, ox = 0, oy = 0;
  for (const z of zooms) {
    const ease = 0.35;
    const k = interpolate(t, [z.from, z.from + ease, z.to - ease, z.to], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
    if (k > 0) {
      scale = 1 + (z.scale - 1) * k;
      ox = (0.5 - z.x) * 1080 * (z.scale - 1) * k;
      oy = (0.5 - z.y) * 1920 * (z.scale - 1) * k;
    }
  }
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ transform: `translate(${ox}px, ${oy}px) scale(${scale})`, transformOrigin: "50% 50%" }}>
        <OffthreadVideo src={staticFile(video)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      {procedures.map((p, i) => (
        <Sequence key={`p${i}`} from={Math.round(p.from * fps)} durationInFrames={Math.max(1, Math.round((p.to - p.from) * fps))}>
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: TOP[p.position] ?? TOP.top }}>
            <ProcedureCard title={p.title} steps={p.steps.map((s) => ({ ...s, at: s.at - p.from }))} seconds={p.to - p.from} />
          </AbsoluteFill>
        </Sequence>
      ))}
      <FxLayer items={fx} />
    </AbsoluteFill>
  );
};
