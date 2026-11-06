import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { defaultTheme } from "../theme";

export interface TerminalLine {
  text: string;
  isError?: boolean;
}

export interface TerminalAnimationProps {
  lines: TerminalLine[];
  cps?: number;          // characters per second
  errorColor?: string;
  textColor?: string;
  background?: string;
  fontSize?: number;
}

// Typewriter animation for a list of lines. Errors can be color-coded.
export const TerminalAnimation: React.FC<TerminalAnimationProps> = ({
  lines,
  cps = 60,
  errorColor,
  textColor,
  background = "#0a0a0b",
  fontSize = 24,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = defaultTheme;
  const err = errorColor ?? t.colors.error;
  const fg = textColor ?? "#a8e6a3";

  // How many characters have been typed so far (total across all lines)?
  const charsPerFrame = cps / fps;
  const totalTyped = Math.floor(frame * charsPerFrame);

  let remaining = totalTyped;
  const rendered: { text: string; isError?: boolean }[] = [];
  for (const line of lines) {
    if (remaining <= 0) break;
    const take = Math.min(remaining, line.text.length);
    rendered.push({ text: line.text.slice(0, take), isError: line.isError });
    remaining -= take;
    if (take < line.text.length) break;
  }

  return (
    <div
      style={{
        background,
        padding: 32,
        fontFamily: t.fonts.mono,
        fontSize,
        color: fg,
        borderRadius: 8,
        minHeight: 400,
        whiteSpace: "pre-wrap",
      }}
    >
      {rendered.map((line, i) => (
        <div key={i} style={{ color: line.isError ? err : fg }}>
          {line.text}
          {i === rendered.length - 1 && frame % fps < fps / 2 && <span>▊</span>}
        </div>
      ))}
    </div>
  );
};
