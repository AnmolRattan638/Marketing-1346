// Look of the motion-graphic scenes. Own palette (the reference reels' cream/red is not copied): deep ink blue, gold, hot pink.
export const THEME = {
  bgTop: "#0B1020",
  bgBottom: "#1A2347",
  card: "#151D3B",
  cardEdge: "rgba(255,255,255,0.14)",
  ink: "#05070F",
  text: "#FFFFFF",
  muted: "rgba(255,255,255,0.68)",
  accent: "#FFD400",
  accent2: "#FF9F1C",
  hot: "#FF3D71",
  ok: "#35D07F",
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
