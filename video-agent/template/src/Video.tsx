import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { useManifest } from "./hooks/useManifest";
import { NarrationTrack } from "./audio/NarrationTrack";
import { MusicBed } from "./audio/MusicBed";
import { SFXCue } from "./audio/SFXCue";
import type { NarrationRange } from "./audio/useDucking";
import ExampleScene from "./sequences/ExampleScene";
import KitchenSink from "./sequences/KitchenSink";
import FootageScene from "./sequences/FootageScene";
import { LogoBug } from "./components/LogoBug";

// Map of component path (as used in manifest.scenes[].component) to the
// actual React component. Add entries here as you create new scene files.
const sceneRegistry: Record<string, React.ComponentType<any>> = {
  "sequences/ExampleScene": ExampleScene,
  "sequences/KitchenSink": KitchenSink,
  "sequences/FootageScene": FootageScene,
};

export const Video: React.FC = () => {
  const manifest = useManifest();

  // Compute each scene's start frame and duration-in-frames from the manifest.
  // durationFromAudio paths are resolved at build time by the Root-level
  // composition setup (see Root.tsx); here we trust manifest.scenes[].duration.
  const fps = manifest.video.fps;
  const narrationRanges: NarrationRange[] = [];
  let cursor = 0;
  const resolved = manifest.scenes.map((s) => {
    const dur = s.duration ?? 0;
    const durFrames = Math.round(dur * fps);
    const startFrame = cursor;
    cursor += durFrames;
    if (s.narration) {
      narrationRanges.push({ startFrame, endFrame: startFrame + durFrames });
    }
    return { scene: s, startFrame, durationFrames: durFrames };
  });

  return (
    <AbsoluteFill>
      {/* Music bed sits at the root so it plays continuously */}
      {manifest.audio.music && (
        <MusicBed
          src={manifest.audio.music.src}
          baseVolume={manifest.audio.music.baseVolume}
          duckTo={manifest.audio.music.duckTo}
          narrationRanges={narrationRanges}
        />
      )}

      {resolved.map(({ scene, startFrame, durationFrames }) => {
        const SceneComponent = sceneRegistry[scene.component];
        if (!SceneComponent) {
          throw new Error(
            `Scene component "${scene.component}" not in sceneRegistry. Register it in Video.tsx.`
          );
        }
        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationFrames}
            name={scene.id}
          >
            <SceneComponent {...(scene.props ?? {})} />
            {scene.narration && <NarrationTrack src={scene.narration} />}
            {scene.sfx.map((cue, i) => (
              <SFXCue key={i} src={cue.src} atSecond={cue.atSecond} volume={cue.volume} />
            ))}
          </Sequence>
        );
      })}
      {manifest.brand?.logo && <LogoBug logo={manifest.brand.logo} />}
    </AbsoluteFill>
  );
};
