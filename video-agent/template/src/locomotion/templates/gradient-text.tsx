// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const GradientText: React.FC<{ text?: string; bgColor?: string; variant?: string }> = ({
  text = 'Captivating', bgColor = THEME.bgTop, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  // Text scales in from 0.85 to 1
  const scaleProgress = interpolate(frame, [0, 20], [0.85, 1], { extrapolateRight: 'clamp' })
  const opacityProgress = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' })

  // Gradient sweep moves from left to right across the text
  const gradientPos = interpolate(frame, [5, fps * 2], [-100, 200], { extrapolateRight: 'clamp' })

  // Determine if bg is dark to pick fallback text color
  const isDark = bgColor === THEME.bgTop || bgColor === THEME.bgTop || bgColor === THEME.bgTop ||
    (bgColor.startsWith('#') && parseInt(bgColor.slice(1, 3), 16) < 80)

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <div style={{
        fontSize: 120,
        fontWeight: 800,
        fontFamily: s.fontFamily,
        letterSpacing: '-0.04em',
        opacity: opacityProgress,
        transform: `scale(${scaleProgress})`,
        background: `linear-gradient(90deg, ${THEME.accent2} ${gradientPos - 60}%, ${THEME.hot} ${gradientPos - 20}%, ${THEME.accent} ${gradientPos + 20}%, ${isDark ? THEME.text : THEME.bgTop} ${gradientPos + 60}%)`,
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        lineHeight: 1.1,
        textAlign: 'center',
        maxWidth: '80%',
      }}>
        {text}
      </div>
    </AbsoluteFill>
  )
}
