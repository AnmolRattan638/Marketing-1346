import React from "react";
import { useFrameSpring } from "../hooks/useFrameSpring";
import { defaultTheme } from "../theme";

export interface CategoryPillProps {
  label: string;
  active?: boolean;
  delay?: number; // frames
  activeColor?: string;
}

// Animated chip — scales in from the parent's start frame + delay.
export const CategoryPill: React.FC<CategoryPillProps> = ({
  label,
  active = false,
  delay = 0,
  activeColor,
}) => {
  const t = defaultTheme;
  const scale = useFrameSpring({ from: 0, to: 1, delay, damping: 12, stiffness: 180 });
  const bg = active ? (activeColor ?? t.colors.accent) : t.colors.mute + "33";
  const fg = active ? "#ffffff" : t.colors.fg;

  return (
    <div
      style={{
        display: "inline-flex",
        padding: "8px 20px",
        borderRadius: 999,
        background: bg,
        color: fg,
        fontFamily: t.fonts.body,
        fontSize: 18,
        fontWeight: 500,
        transform: `scale(${scale})`,
        transformOrigin: "center",
      }}
    >
      {label}
    </div>
  );
};
