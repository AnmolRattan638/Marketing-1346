import { Audio, staticFile } from "remotion";

export interface NarrationTrackProps {
  src: string; // path relative to project root, e.g. "assets/audio/narration/s3.mp3"
  volume?: number;
}

// A narration voice-over clip. The parent <Sequence> is responsible for
// setting duration (derived from manifest.durationFromAudio). This component
// only plays the audio.
export const NarrationTrack: React.FC<NarrationTrackProps> = ({
  src,
  volume = 1.0,
}) => {
  return <Audio src={staticFile(src)} volume={volume} />;
};
