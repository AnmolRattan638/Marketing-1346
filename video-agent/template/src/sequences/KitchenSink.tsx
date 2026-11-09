import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { TitleCard } from "../components/TitleCard";
import { TerminalAnimation } from "../components/TerminalAnimation";
import { UIFrame } from "../components/UIFrame";
import { KenBurns } from "../components/KenBurns";
import { StatReveal } from "../components/StatReveal";
import { ProgressBar } from "../components/ProgressBar";
import { CategoryPill } from "../components/CategoryPill";
import { ComparisonSlide } from "../components/ComparisonSlide";
import { FadeTransition } from "../components/FadeTransition";
import { defaultTheme } from "../theme";

export interface KitchenSinkProps {
  // Scene is parameterless for simplicity; content hard-coded to keep the
  // example focused on component coverage.
}

// Kitchen-sink demo scene — renders every shipped component at least once,
// time-sliced into six phases spanning 600 frames (20s @ 30fps). Exists as a
// visual reference and a compile-time smoke test that each component's public
// API still type-checks against the rest of the template.
export const KitchenSink: React.FC<KitchenSinkProps> = () => {
  const t = defaultTheme;
  return (
    <AbsoluteFill style={{ background: t.colors.bg }}>
      {/* Phase A — Title 0–90 (0–3s) */}
      <Sequence from={0} durationInFrames={90} name="A_title">
        <FadeTransition durationFrames={10} direction="both">
          <TitleCard
            title="Component Kitchen Sink"
            subtitle="Every component, on one reel"
          />
        </FadeTransition>
      </Sequence>

      {/* Phase B — Terminal 90–210 (3–7s) */}
      <Sequence from={90} durationInFrames={120} name="B_terminal">
        <FadeTransition durationFrames={10} direction="both">
          <AbsoluteFill style={{ padding: 96, justifyContent: "center" }}>
            <TerminalAnimation
              lines={[
                { text: "$ claude-remotion scaffold my-video" },
                { text: "> copying template..." },
                { text: "> installing dependencies..." },
                {
                  text: "Error: ENOENT: no such file 'manifest.json'",
                  isError: true,
                },
                { text: "$ bash scripts/scaffold.sh my-video" },
                { text: "> done." },
              ]}
              cps={40}
            />
          </AbsoluteFill>
        </FadeTransition>
      </Sequence>

      {/* Phase C — Screenshot 210–330 (7–11s) */}
      <Sequence from={210} durationInFrames={120} name="C_screenshot">
        <FadeTransition durationFrames={10} direction="both">
          <AbsoluteFill
            style={{ alignItems: "center", justifyContent: "center" }}
          >
            <UIFrame url="https://example.com" width={1400} height={800}>
              <KenBurns
                src="assets/screenshots/demo.png"
                from={{ scale: 1, x: 0, y: 0 }}
                to={{ scale: 1.15, x: -40, y: -20 }}
              />
            </UIFrame>
          </AbsoluteFill>
        </FadeTransition>
      </Sequence>

      {/* Phase D — Stats 330–420 (11–14s) */}
      <Sequence from={330} durationInFrames={90} name="D_stats">
        <FadeTransition durationFrames={10} direction="both">
          <AbsoluteFill
            style={{
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "space-around",
              padding: 128,
            }}
          >
            <StatReveal value={277} label="strains" fontSize={160} />
            <ProgressBar
              value={0.83}
              label="pipeline completeness"
              width={500}
            />
          </AbsoluteFill>
        </FadeTransition>
      </Sequence>

      {/* Phase E — Pills 420–510 (14–17s) */}
      <Sequence from={420} durationInFrames={90} name="E_pills">
        <FadeTransition durationFrames={10} direction="both">
          <AbsoluteFill
            style={{
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              gap: 16,
            }}
          >
            <CategoryPill label="Ester Production" delay={0} />
            <CategoryPill label="Alcohol Tolerance" delay={8} active />
            <CategoryPill label="Flocculation" delay={16} />
            <CategoryPill label="Sulfur Pathways" delay={24} />
          </AbsoluteFill>
        </FadeTransition>
      </Sequence>

      {/* Phase F — Comparison 510–600 (17–20s) */}
      <Sequence from={510} durationInFrames={90} name="F_comparison">
        <FadeTransition durationFrames={10} direction="both">
          <ComparisonSlide
            leftLabel="Before"
            rightLabel="After"
            left={
              <div style={{ fontSize: 48, color: t.colors.mute }}>
                Manual pipelines
              </div>
            }
            right={
              <div style={{ fontSize: 48, color: t.colors.success }}>
                One upload
              </div>
            }
          />
        </FadeTransition>
      </Sequence>
    </AbsoluteFill>
  );
};

export default KitchenSink;
