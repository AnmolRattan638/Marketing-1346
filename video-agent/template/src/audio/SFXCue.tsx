import { Audio, Sequence, staticFile, useVideoConfig } from "remotion";

export interface SFXCueProps {
  src: string;
  atSecond: number;
  volume?: number;
}

// A fire-and-forget one-shot sound effect anchored at atSecond within its
// parent <Sequence>. Use inside scene components that receive their manifest
// sfx array.
export const SFXCue: React.FC<SFXCueProps> = ({ src, atSecond, volume = 1.0 }) => {
  const { fps } = useVideoConfig();
  const fromFrame = Math.max(0, Math.round(atSecond * fps));
  return (
    <Sequence from={fromFrame}>
      <Audio src={staticFile(src)} volume={volume} />
    </Sequence>
  );
};
