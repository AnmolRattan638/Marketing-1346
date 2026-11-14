// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, interpolate } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const TypewriterReveal: React.FC<{ text?: string; variant?: string }> = ({
  text = 'Building the future.',
  variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const chars = Math.floor(
    interpolate(frame, [0, 70], [0, text.length], { extrapolateRight: 'clamp' })
  )
  const cursorOpacity = Math.round(frame / 8) % 2 === 0 ? 1 : 0

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <div style={{
        fontFamily: s.fontFamily, fontSize: isMono ? 40 : 46, color: THEME.text,
        fontWeight: s.fontWeight, letterSpacing: s.letterSpacing,
        textTransform: isMono ? 'uppercase' as const : 'none' as const,
      }}>
        {text.slice(0, chars)}
        <span style={{ opacity: cursorOpacity, color: THEME.muted }}>|</span>
      </div>
    </AbsoluteFill>
  )
}
