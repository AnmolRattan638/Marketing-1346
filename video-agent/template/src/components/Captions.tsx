import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

export interface CaptionWord {
  text: string;
  start: number; // seconds from the start of the scene
  end: number;
}

export interface CaptionsProps {
  words: CaptionWord[];
  wordsPerChunk?: number;
  activeColor?: string;
}

// Word-by-word captions: shows a short chunk of words and highlights the one
// being spoken. Timings come from Whisper (or an even-split estimate).
export const Captions: React.FC<CaptionsProps> = ({
  words,
  wordsPerChunk = 3,
  activeColor = "#FFD400",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (words.length === 0) return null;

  const t = frame / fps;
  // Index of the word being spoken (or the last one already spoken).
  let active = 0;
  for (let i = 0; i < words.length; i++) {
    if (words[i].start <= t) active = i;
  }
  const chunkStart = Math.floor(active / wordsPerChunk) * wordsPerChunk;
  const chunk = words.slice(chunkStart, chunkStart + wordsPerChunk);

  return (
    <AbsoluteFill
      style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 380 }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "10px 22px",
          maxWidth: 940,
          fontFamily:
            '"Noto Sans Devanagari", "Noto Sans", "Helvetica Neue", Arial, sans-serif',
          fontWeight: 800,
          fontSize: 84,
          lineHeight: 1.12,
          textAlign: "center",
        }}
      >
        {chunk.map((w, i) => {
          const isActive = chunkStart + i === active;
          return (
            <span
              key={chunkStart + i}
              style={{
                color: isActive ? activeColor : "white",
                transform: `scale(${isActive ? 1.08 : 1})`,
                textShadow:
                  "0 0 6px rgba(0,0,0,0.9), 0 4px 14px rgba(0,0,0,0.7), 3px 3px 0 rgba(0,0,0,0.85), -3px -3px 0 rgba(0,0,0,0.85), 3px -3px 0 rgba(0,0,0,0.85), -3px 3px 0 rgba(0,0,0,0.85)",
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
