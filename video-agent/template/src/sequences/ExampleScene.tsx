import React from "react";
import { AbsoluteFill } from "remotion";
import { TitleCard } from "../components/TitleCard";
import { StatReveal } from "../components/StatReveal";
import { defaultTheme } from "../theme";

export interface ExampleSceneProps {
  title?: string;
  subtitle?: string;
}

// Worked example scene — fork this when creating S1/S2/etc. scenes of your
// own. Consumes props passed via manifest.scenes[].props.
export const ExampleScene: React.FC<ExampleSceneProps> = ({
  title = "Hello, Remotion",
  subtitle = "Edit manifest.json to customize",
}) => {
  const t = defaultTheme;
  return (
    <AbsoluteFill style={{ background: t.colors.bg }}>
      <TitleCard
        title={title}
        subtitle={subtitle}
        footnote="Template example — safe to delete when building your own scenes"
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 96 }}>
        <StatReveal value={277} label="example count" fontSize={80} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export default ExampleScene;
