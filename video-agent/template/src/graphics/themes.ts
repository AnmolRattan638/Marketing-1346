import { THEME } from "./theme";

// The reel's colours come ONLY from the brand palette (config.json -> brand.palette, extracted from the website's CSS variables by agent/brand.py).
// Video.tsx calls applyTheme(manifest.look.palette) before the first frame, so every component that reads THEME follows it.
const BASE = { ...THEME };
export function applyTheme(palette?: Partial<typeof THEME>) {
  Object.assign(THEME, BASE, palette ?? {});
}
