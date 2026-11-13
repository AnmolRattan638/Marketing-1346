import React from "react";
import {
  AbsoluteFill,
  Loop,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CaptionWord } from "../components/Captions";
import { CaptionLayer, CaptionStyle, CaptionZone } from "../components/CaptionStyles";
import { FxItem, FxLayer } from "../effects/FxLayer";
import { FilmGrain } from "../effects/FilmGrain";
import { Arrival, arrival, shake } from "../effects/motion";
import { CameraMove, cameraAt } from "../effects/camera";

export interface FootageSceneProps {
  clip: string; // e.g. "assets/run/footage/s1.mp4"
  clipSeconds: number; // length of the clip, so short clips can loop
  words: CaptionWord[];
  emphasis?: string[]; // words the captions emphasise
  pulses?: number[]; // seconds (from the scene start) of emphasis words: the picture punches in on each, in sync with the pop/riser
  overlayText?: string; // call to action, shown near the end of the scene
  zoom?: number; // total slow zoom over the scene, 0.04 = 4%
  fadeOutFrames?: number; // fade to black at the END of the scene; only the last scene of the video uses it
  upperCaptions?: boolean;
  fx?: FxItem[]; // animated graphics and camera shakes anchored to spoken words (agent/fx_plan.py)
  transitionIn?: Arrival; // how the scene arrives: settle | whip | zoom | iris | glitch
  camera?: CameraMove[]; // zoom / pan moves on the footage (agent/camera_plan.py)
  captionZones?: CaptionZone[]; // smart caption placement for this scene
  captionStyle?: CaptionStyle; // from the reel's look (agent/looks.py)
  grain?: number; // film grain strength, 0 = off
}

// One scene of the reel. The footage was already cut on the spoken words (agent/hybrid.py); here it gets a slow push,
// a settle on the scene cut (landing with the whoosh), a punch-in on every emphasis word (landing with the pop),
// animated captions, and the optional call to action. Scene cuts are hard cuts: no dip to black.
const FootageScene: React.FC<FootageSceneProps> = ({
  clip,
  clipSeconds,
  words,
  emphasis = [],
  pulses = [],
  overlayText,
  zoom = 0.04,
  fadeOutFrames = 0,
  upperCaptions = true,
  fx = [],
  transitionIn = "settle",
  captionStyle, captionZones, camera = [], grain = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const clipFrames = Math.max(1, Math.round(clipSeconds * fps));
  const cm = camera.length ? cameraAt(camera, frame / fps) : null;
  const push = cm ? 0 : interpolate(frame, [0, durationInFrames], [0, zoom]); // directed camera replaces the slow push
  const punch = pulses.reduce((sum, p) => {
    const f = frame - Math.round(p * fps);
    if (f < 0 || f > 24) return sum;
    return sum + 0.05 * (f < 2 ? f / 2 : Math.exp(-(f - 2) / 4));
  }, 0);
  const look = arrival(transitionIn, frame, fps); // how this scene lands (settle = slight zoom that eases back with the whoosh)
  const cam = shake(frame, fps, fx.filter((f) => f.type === "shake")); // camera shake on impact words, footage only: captions stay still
  const scale = (1 + push + punch) * look.scale * cam.scale * (cm ? cm.scale : 1);

  const fadeOut =
    fadeOutFrames > 0
      ? interpolate(frame, [durationInFrames - fadeOutFrames, durationInFrames], [1, 0], { extrapolateLeft: "clamp" })
      : 1;

  const ctaStart = durationInFrames - Math.round(2 * fps);
  const cta = spring({ frame: frame - ctaStart, fps, config: { damping: 11, stiffness: 200, mass: 0.7 } });

  return (
    <AbsoluteFill style={{ backgroundColor: "black", opacity: fadeOut }}>
      <AbsoluteFill
        style={{
          transform: `translate(${look.translateX + cam.x + (cm ? cm.x : 0)}px, ${look.translateY + cam.y + (cm ? cm.y : 0)}px) scale(${scale})`,
          filter: look.blur || look.hue || look.brightness !== 1 ? `blur(${look.blur}px) hue-rotate(${look.hue}deg) brightness(${look.brightness})` : undefined,
          opacity: look.opacity,
          clipPath: look.clip,
        }}
      >
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
            "linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 48%), radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.28) 100%)",
        }}
      />
      <FxLayer items={fx} />
      <CaptionLayer words={words} emphasis={emphasis} upper={upperCaptions} style={captionStyle} zones={captionZones} />
      {grain > 0 ? <FilmGrain opacity={grain} /> : null}
      {overlayText ? (
        <AbsoluteFill
          style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 260 }}
        >
          <div
            style={{
              opacity: Math.min(1, Math.max(0, cta)),
              transform: `translateY(${(1 - Math.min(1, Math.max(0, cta))) * -40}px) scale(${0.85 + 0.15 * Math.max(0, cta)})`,
              background: "linear-gradient(135deg, #FFD400, #FF9F1C)",
              boxShadow: "0 14px 44px rgba(255,159,28,0.45)",
              color: "#111",
              fontFamily:
                '"Montserrat", "Poppins", "Noto Sans Devanagari", "Noto Sans", "Helvetica Neue", Arial, sans-serif',
              fontWeight: 900,
              fontSize: 64,
              padding: "20px 44px",
              borderRadius: 26,
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
