import { THEME } from "./theme";

// Colour looks. A reel picks one (agent/looks.py) and Video.tsx applies it before the first frame, so every component that reads THEME follows.
export const THEMES: Record<string, Partial<typeof THEME>> = {
  ink: {},
  sunset: { bgTop: "#1B0B1E", bgBottom: "#44123A", card: "#2A1230", accent: "#FF9F1C", accent2: "#FFD400", hot: "#FF3D71", ink: "#12040F" },
  forest: { bgTop: "#06201C", bgBottom: "#0E3B33", card: "#0C2E29", accent: "#5CF2C0", accent2: "#B6FF6B", hot: "#FF6B6B", ink: "#03130F" },
  violet: { bgTop: "#12082B", bgBottom: "#2E1A6B", card: "#1E1048", accent: "#B79CFF", accent2: "#FFD400", hot: "#FF4FA3", ink: "#090417" },
};
const BASE = { ...THEME };
export function applyTheme(name?: string) {
  Object.assign(THEME, BASE, THEMES[name ?? "ink"] ?? {});
}
