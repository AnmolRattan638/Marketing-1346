import React from "react";
import {
  AbsoluteFill,
  Loop,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Captions, CaptionWord } from "../components/Captions";

export interface FootageSceneProps {
  clip: string; // e.g. "assets/run/footage/s1.mp4"
  clipSeconds: number; // length of the clip, so short clips can loop
  words: CaptionWord[];
  overlayText?: string; // call to action, shown near the end of the scene
  zoom?: number; // total slow zoom over the scene, 0.06 = 6%
  fadeFrames?: number;
}

// One stock-footage scene: looped muted clip with a slow zoom, a fade at the
// cut, a shade under the captions, and optional end-of-video call to action.
const FootageScene: React.FC<FootageSceneProps> = ({
  clip,
  clipSeconds,
  words,
  overlayText,
  zoom = 0.06,
  fadeFrames = 8,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const clipFrames = Math.max(1, Math.round(clipSeconds * fps));
  const scale = 1 + interpolate(frame, [0, durationInFrames], [0, zoom]);
  const fadeIn = interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fadeFrames, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp" }
  );

  const ctaStart = durationInFrames - Math.round(2 * fps);
  const ctaOpacity = interpolate(frame, [ctaStart, ctaStart + 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "black", opacity: Math.min(fadeIn, fadeOut) }}>
      <AbsoluteFill style={{ transform: `scale(${scale})` }}>
        <Loop durationInFrames={clipFrames}>
          <OffthreadVideo
            src={staticFile(clip)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </Loop>
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 45%)",
        }}
      />
      <Captions words={words} />
      {overlayText ? (
        <AbsoluteFill
          style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 260 }}
        >
          <div
            style={{
              opacity: ctaOpacity,
              background: "#FFD400",
              color: "#111",
              fontFamily:
                '"Noto Sans Devanagari", "Noto Sans", "Helvetica Neue", Arial, sans-serif',
              fontWeight: 800,
              fontSize: 64,
              padding: "20px 44px",
              borderRadius: 22,
              maxWidth: 900,
              textAlign: "center",
            }}
          >
            {overlayText}
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

export default FootageScene;
