export interface ManifestVideo {
  id: string;
  width: number;
  height: number;
  fps: number;
  title: string;
}

export interface ManifestMusic {
  src: string;
  baseVolume: number;
  duckTo: number;
}

export interface ManifestAudio {
  music: ManifestMusic | null;
}

export interface ManifestSfxCue {
  src: string;
  atSecond: number;
  volume?: number;
}

export interface ManifestScene {
  id: string;
  component: string;
  duration?: number;
  durationFromAudio?: string;
  narration: string | null;
  sfx: ManifestSfxCue[];
  props?: Record<string, unknown>;
}

export interface ManifestLogo {
  src: string;
  position?: "top-left" | "top-right" | "bottom-left" | "bottom-right";
  size?: number;
  opacity?: number;
  marginX?: number;
  marginY?: number;
}

export interface Manifest {
  brand?: { logo: ManifestLogo | null };
  video: ManifestVideo;
  audio: ManifestAudio;
  scenes: ManifestScene[];
}
