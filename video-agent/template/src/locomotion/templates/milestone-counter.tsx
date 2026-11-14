// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const MilestoneCounter: React.FC<{ label?: string; value?: string; emoji?: string; bgColor?: string; variant?: string }> = ({
  label = 'Followers', value = '+1,300', emoji = '\uD83D\uDD25', bgColor = THEME.hot, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  const emojiS = spring({ frame, fps, config: { stiffness: 300, damping: 10 } })
  const labelS = spring({ frame: frame - 8, fps, config: { stiffness: 200, damping: 18 } })
  const numberS = spring({ frame: frame - 14, fps, config: { stiffness: 120, damping: 16 } })

  // Parse number for rolling animation
  const prefix = value.match(/^[^0-9]*/)?.[0] ?? ''
  const numericStr = value.replace(/[^0-9]/g, '')
  const numericVal = parseInt(numericStr, 10) || 0
  const animatedNum = Math.round(interpolate(numberS, [0, 1], [0, numericVal]))

  // Slight bg gradient
  const gradientAngle = interpolate(frame, [0, 90], [135, 180], { extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill style={{
      justifyContent: 'center', alignItems: 'center',
      background: `linear-gradient(${gradientAngle}deg, ${bgColor}, ${bgColor}cc)`,
    }}>
      <div style={{ textAlign: 'center' }}>
        {/* Emoji with bounce */}
        <div style={{
          fontSize: 80, marginBottom: 20,
          transform: `scale(${emojiS})`,
          filter: `drop-shadow(0 4px 12px rgba(6,8,13,0.2))`,
        }}>
          {/* Emoji in a dark pill */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 120, height: 120, borderRadius: 999,
            backgroundColor: `rgba(6,8,13,0.7)`, fontSize: 56,
          }}>
            {emoji}
          </div>
        </div>

        {/* Label */}
        <div style={{
          fontSize: 28, fontWeight: 600, color: THEME.card, fontFamily: s.fontFamily,
          opacity: labelS, marginBottom: 8,
          letterSpacing: s.letterSpacing,
          textShadow: `0 2px 8px rgba(6,8,13,0.2)`,
        }}>
          {label}
        </div>

        {/* Big rolling number */}
        <div style={{
          fontSize: 96, fontWeight: 800, color: THEME.card, fontFamily: s.fontFamily,
          letterSpacing: '-0.03em',
          opacity: numberS,
          transform: `translateY(${interpolate(numberS, [0, 1], [20, 0])}px)`,
          textShadow: `0 4px 16px rgba(6,8,13,0.3)`,
        }}>
          {prefix}{animatedNum.toLocaleString()}
        </div>
      </div>
    </AbsoluteFill>
  )
}
