// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const CountdownTimer: React.FC<{ text?: string; variant?: string }> = ({ text = 'Launching soon', variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const titleS = spring({ frame, fps, config: { stiffness: 200, damping: 20 } })
  const units = [
    { v: Math.max(0, Math.floor(interpolate(frame, [10, 80], [12, 0], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' }))), l: 'DAYS' },
    { v: Math.max(0, Math.floor(interpolate(frame, [10, 80], [8, 0], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' }))), l: 'HRS' },
    { v: Math.max(0, Math.floor(interpolate(frame, [10, 80], [45, 0], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' }))), l: 'MIN' },
  ]

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <h2 style={{
        fontSize: isMono ? 28 : 32, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily,
        marginBottom: 24, opacity: titleS, letterSpacing: s.letterSpacing,
        textTransform: isMono ? 'uppercase' as const : 'none' as const,
      }}>{text}</h2>
      <div style={{ display: 'flex', gap: 12 }}>
        {units.map((u, i) => {
          const sp = spring({ frame: frame - 5 - i * 5, fps, config: { stiffness: 200, damping: 16 } })
          return (
            <div key={i} style={{
              width: 80, padding: '16px 0', borderRadius: s.borderRadius,
              border: `${s.borderWidth}px solid ${s.borderColor}`, backgroundColor: THEME.card,
              textAlign: 'center', opacity: sp, transform: `scale(${interpolate(sp, [0,1], [0.9,1])})`,
              boxShadow: s.shadow,
            }}>
              <div style={{ fontSize: isMono ? 28 : 32, fontWeight: 800, color: THEME.text, fontFamily: s.fontFamily }}>{String(u.v).padStart(2, '0')}</div>
              <div style={{ fontSize: 9, color: THEME.muted, fontFamily: s.fontFamily, letterSpacing: '0.1em', marginTop: 2 }}>{u.l}</div>
            </div>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}
