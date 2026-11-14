import React from "react";
import { Composition, registerRoot } from "remotion";
import GraphicScene from "../sequences/GraphicScene";
import { applyTheme } from "../graphics/themes";
import { LOCOMOTION } from "../locomotion/registry";

// Preview of every imported template exactly as the reel shows it:  npx remotion still src/lab/index.ts <id> out.png --frame=60 --props='{"variant":"glass","props":{"text":"Hi"},"anchors":[[0,0]]}'
applyTheme();
const mk = (id: string): React.FC<{ variant?: string; props?: Record<string, unknown>; anchors?: [number, number][] }> => ({ variant = "default", props = {}, anchors }) => (
  <GraphicScene layout="tpl" words={[]} times={{ heading: 0, mock: 0, items: [], chips: 0 }} tpl={{ id, variant, props, anchors }} showProgress={false} />
);
export const LabRoot: React.FC = () => (
  <>
    {Object.keys(LOCOMOTION).map((id) => (
      <Composition key={id} id={id} component={mk(id)} durationInFrames={150} fps={30} width={1080} height={1920} defaultProps={{ variant: "default", props: {} }} />
    ))}
  </>
);

