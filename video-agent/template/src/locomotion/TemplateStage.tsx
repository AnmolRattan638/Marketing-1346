import React from "react";
import { AbsoluteFill } from "remotion";
import { THEME } from "../graphics/theme";
import { LOCOMOTION } from "./registry";
import { WarpContext, makeWarp } from "./timewarp";

// The Locomotion templates are 960x540 landscape compositions. Here one is shown as a rounded card, scaled to the reel's width and centred above the caption area.
export const TPL_W = 960;
export const TPL_H = 540;
export const TPL_SCALE = 1.08;

export interface TemplateSpec {
  id: string; // key of LOCOMOTION
  variant?: string; // default | brutalist | rounded | minimal | glass | neo
  props?: Record<string, unknown>;
  atFrame?: number; // fallback: when the template's own animation starts inside the scene
  anchors?: [number, number][]; // [scene frame, template frame]: pins a moment of the template to a spoken word (agent/templates.py)
}

export const TemplateStage: React.FC<TemplateSpec & { top?: number }> = ({ id, variant = "default", props = {}, atFrame = 0, anchors, top = 520 }) => {
  const C = LOCOMOTION[id];
  if (!C) return null;
  const w = TPL_W * TPL_SCALE;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute", left: (1080 - w) / 2, top, width: TPL_W, height: TPL_H, transformOrigin: "top left", transform: `scale(${TPL_SCALE})`,
          borderRadius: 26, overflow: "hidden", border: `2px solid ${THEME.cardEdge}`, boxShadow: `0 0 60px ${THEME.glowSoft}`, backgroundColor: THEME.card,
        }}
      >
        <WarpContext.Provider value={makeWarp(anchors && anchors.length ? anchors : [[atFrame, 0]])}>
          <C variant={variant} {...props} />
        </WarpContext.Provider>
      </div>
    </AbsoluteFill>
  );
};
