// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, interpolate } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const FadeSlideUp: React.FC<{ text?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  text = 'Hello World', textColor = THEME.text, bgColor = THEME.card, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const s = getCompositionStyles(variant)
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' })
  const translateY = interpolate(frame, [0, 20], [20, 0], { extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <h1 style={{
        fontSize: 72, fontWeight: s.fontWeight, color: textColor, opacity,
        transform: `translateY(${translateY}px)`, fontFamily: s.fontFamily,
        letterSpacing: s.letterSpacing,
      }}>{text}</h1>
    </AbsoluteFill>
  )
}
