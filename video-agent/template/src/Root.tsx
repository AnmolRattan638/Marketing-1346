import React from "react";
import { Composition } from "remotion";
import { Video } from "./Video";
import manifest from "../manifest.json";
import type { Manifest } from "./types";

const m = manifest as Manifest;

// Total duration = sum of all scene durations. durationFromAudio is resolved
// via the measure-audio.sh script — the resulting seconds must be written
// back into manifest.scenes[].duration by the author (or director skill).
const totalSeconds = m.scenes.reduce((acc, s) => acc + (s.duration ?? 0), 0);
const totalFrames = Math.max(1, Math.round(totalSeconds * m.video.fps));

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Main"
        component={Video}
        durationInFrames={totalFrames}
        fps={m.video.fps}
        width={m.video.width}
        height={m.video.height}
      />
    </>
  );
};
