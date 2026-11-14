// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const ToggleSwitch: React.FC<{ text?: string; bgColor?: string; textColor?: string; variant?: string }> = ({
  text = 'Video', bgColor = THEME.accent2, textColor = THEME.accent2, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  // Toggle animates on at frame 15
  const toggleS = spring({ frame: frame - 15, fps, config: { stiffness: 200, damping: 14 } })

  // Track background goes from gray to colored
  const trackColor = interpolate(toggleS, [0, 1], [0, 1])

  // Knob slides from left to right
  const knobX = interpolate(toggleS, [0, 1], [6, 126])

  // Overall entrance
  const entranceS = spring({ frame, fps, config: { stiffness: 180, damping: 18 } })

  // Text fade in
  const textS = spring({ frame: frame - 5, fps, config: { stiffness: 200, damping: 20 } })

  // Gradient background
  const gradientAngle = interpolate(frame, [0, 90], [120, 200], { extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill style={{
      justifyContent: 'center', alignItems: 'center',
      background: `linear-gradient(${gradientAngle}deg, ${bgColor}, ${bgColor}88, ${bgColor}cc)`,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center',
        backgroundColor: THEME.card, borderRadius: 999,
        padding: '16px 24px 16px 32px', gap: 16,
        opacity: entranceS,
        transform: `scale(${interpolate(entranceS, [0, 1], [0.8, 1])})`,
        boxShadow: `0 8px 32px rgba(6,8,13,0.15)`,
      }}>
        {/* Text label */}
        <span style={{
          fontSize: 48, fontWeight: 800, color: THEME.text, fontFamily: s.fontFamily,
          opacity: textS, letterSpacing: '-0.02em',
        }}>
          {text}
        </span>

        {/* Toggle track */}
        <div style={{
          width: 200, height: 80, borderRadius: 999, position: 'relative',
          backgroundColor: `rgba(240,192,64, ${0.15 + trackColor * 0.85})`,
          transition: 'background-color 0.1s',
        }}>
          {/* Knob */}
          <div style={{
            width: 68, height: 68, borderRadius: 999,
            backgroundColor: trackColor > 0.5 ? textColor : THEME.cardEdge,
            position: 'absolute', top: 6,
            left: knobX,
            boxShadow: `0 2px 8px rgba(6,8,13,0.15)`,
          }} />
        </div>
      </div>
    </AbsoluteFill>
  )
}
