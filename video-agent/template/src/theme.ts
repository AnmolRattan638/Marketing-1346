// Default theme tokens. Aesthetic-neutral grayscale — override by editing
// this file directly. Changes apply to all scenes.

export interface Theme {
  colors: {
    bg: string;
    fg: string;
    mute: string;
    accent: string;
    success: string;
    warn: string;
    error: string;
  };
  fonts: {
    display: string;
    body: string;
    mono: string;
  };
  spacing: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
    xl: number;
  };
}

export const defaultTheme: Theme = {
  colors: {
    bg: "#0f0f10",
    fg: "#e8e8ea",
    mute: "#8a8a90",
    accent: "#6b8cff",
    success: "#4ade80",
    warn: "#f59e0b",
    error: "#ef4444",
  },
  fonts: {
    display: "Inter, system-ui, sans-serif",
    body: "Inter, system-ui, sans-serif",
    mono: "JetBrains Mono, Menlo, monospace",
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 32,
    xl: 64,
  },
};
