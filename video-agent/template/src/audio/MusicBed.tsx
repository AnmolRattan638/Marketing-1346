import { Audio, staticFile } from "remotion";
import { makeDuckingVolume, NarrationRange } from "./useDucking";

export interface MusicBedProps {
  src: string;
  baseVolume: number;
  duckTo: number;
  narrationRanges: NarrationRange[];
  rampFrames?: number;
}

// Continuous music bed for the entire composition. Sits at the root of
// <Video> (outside all <Sequence>s) and ducks under each narration range.
export const MusicBed: React.FC<MusicBedProps> = ({
  src,
  baseVolume,
  duckTo,
  narrationRanges,
  rampFrames,
}) => {
  const volumeFn = makeDuckingVolume({
    ranges: narrationRanges,
    baseVolume,
    duckTo,
    rampFrames,
  });
  return <Audio src={staticFile(src)} volume={volumeFn} />;
};
