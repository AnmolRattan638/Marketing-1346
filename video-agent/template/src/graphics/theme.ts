// Look of the motion-graphic scenes. STRICTLY the brand palette from the website (agent/brand.py extracts it from index.html into config.json -> brand.palette): black, navy, gold. No other colours.
export const THEME = {
  bgTop: "#06080D", // --black
  bgBottom: "#0A1220", // --navy
  card: "#0D182B", // --navy-card
  cardEdge: "#1A2A44", // --navy-border
  ink: "#06080D",
  text: "#E8EBF2", // --text
  muted: "#9AA3B2", // --muted
  accent: "#F0C040", // --gold-bright
  accent2: "#C9A84C", // --gold
  hot: "#FFF0B3", // --gold-light: where the old palette used a loud second colour, emphasis is gold-light now
  ok: "#F0C040",
  glow: "rgba(240,192,64,0.45)",
  glowSoft: "rgba(240,192,64,0.14)",
};
export const FONT_HEAD =
  '"Montserrat", "Poppins", "Inter", "Noto Sans Devanagari", "Noto Sans", "Helvetica Neue", Arial, sans-serif';
export const FONT_SERIF = '"Playfair Display", "Noto Serif", "DejaVu Serif", Georgia, serif';
export const FONT_MONO = '"JetBrains Mono", "Fira Code", "DejaVu Sans Mono", Menlo, Consolas, monospace';

export interface GraphicTimes {
  heading: number; // seconds from the scene start (the spoken word that introduces the heading)
  mock: number; // the mock-up card appears
  items: number[]; // one per item (list row / terminal line / checklist tick / strike), each on its spoken word
  chips: number;
}
export type MockType = "terminal" | "comment" | "checklist" | "browser" | "file" | "window";
export interface MockSpec {
  type: MockType;
  title?: string;
  items: string[];
  pressAt?: number; // comment box: when POST is pressed
}
