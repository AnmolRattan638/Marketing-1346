// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, interpolate } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const FlashcardFlip: React.FC<{ text?: string; variant?: string }> = ({ text = 'Photosynthesis', variant = 'default' }) => {
  const frame = useCurrentFrame()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const flipProgress = interpolate(frame, [20, 40], [0, 180], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' })
  const showBack = flipProgress > 90
  const scaleX = Math.abs(Math.cos((flipProgress * Math.PI) / 180))

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <div style={{
        width: 360, height: 200, borderRadius: s.borderRadius,
        border: `${s.borderWidth}px solid ${s.borderColor}`,
        backgroundColor: showBack ? THEME.text : THEME.card, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', transform: `scaleX(${scaleX})`, padding: 24,
        boxShadow: s.shadow,
      }}>
        {!showBack ? (
          <>
            <div style={{ fontSize: 12, color: THEME.muted, fontFamily: s.fontFamily, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Question</div>
            <div style={{
              fontSize: isMono ? 22 : 26, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily,
              textAlign: 'center', letterSpacing: s.letterSpacing,
            }}>{text}</div>
          </>
        ) : (
          <>
            <div style={{ fontSize: 12, color: THEME.muted, fontFamily: s.fontFamily, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Answer</div>
            <div style={{ fontSize: isMono ? 14 : 16, color: THEME.card, fontFamily: s.fontFamily, textAlign: 'center', lineHeight: 1.5 }}>The process by which plants convert sunlight into energy</div>
          </>
        )}
      </div>
      <div style={{ fontSize: 11, color: THEME.muted, marginTop: 12, fontFamily: s.fontFamily, opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' }) }}>Tap to flip</div>
    </AbsoluteFill>
  )
}
