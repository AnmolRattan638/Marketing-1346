// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const StaggeredWords: React.FC<{ text?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  text = 'Design. Build. Ship.',
  textColor = THEME.text,
  bgColor = THEME.card,
  variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const words = text.split(' ')

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
        {words.map((word, i) => {
          const delay = i * 6
          const progress = spring({ frame: frame - delay, fps, config: { stiffness: 200, damping: 15 } })
          const y = interpolate(progress, [0, 1], [16, 0])
          return (
            <span key={i} style={{
              fontSize: isMono ? 54 : 62, fontWeight: s.fontWeight, color: textColor, opacity: progress,
              transform: `translateY(${y}px)`, fontFamily: s.fontFamily,
              letterSpacing: s.letterSpacing,
              textTransform: isMono ? 'uppercase' as const : 'none' as const,
            }}>
              {word}
            </span>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}
