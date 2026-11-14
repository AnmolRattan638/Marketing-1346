// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const SpringScaleIn: React.FC<{ text?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  text = 'Welcome', textColor = THEME.text, bgColor = THEME.card, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const scale = spring({ frame, fps, config: { stiffness: 200, damping: 12 } })
  const opacity = spring({ frame, fps, config: { stiffness: 300, damping: 20 } })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <h1 style={{
        fontSize: 82, fontWeight: s.fontWeight, color: textColor,
        transform: `scale(${scale})`, opacity, fontFamily: s.fontFamily,
        letterSpacing: s.letterSpacing,
      }}>{text}</h1>
    </AbsoluteFill>
  )
}
