// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const LevelUp: React.FC<{ variant?: string }> = ({ variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const levelS = spring({ frame, fps, config: { stiffness: 300, damping: 10 } })
  const textS = spring({ frame: frame - 8, fps, config: { stiffness: 200, damping: 16 } })
  const barS = interpolate(frame, [15, 50], [0, 100], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' })
  const shake = frame > 3 && frame < 10 ? Math.sin(frame * 4) * 3 * (1 - (frame - 3) / 7) : 0

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgTop }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 11, color: THEME.muted, fontFamily: s.fontFamily, textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 8, opacity: textS }}>Level Up!</div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 4, transform: `scale(${levelS}) translateX(${shake}px)` }}>
          <span style={{ fontSize: isMono ? 60 : 72, fontWeight: 900, color: THEME.text, fontFamily: s.fontFamily }}>42</span>
          <span style={{ fontSize: isMono ? 17 : 20, fontWeight: s.fontWeight, color: THEME.muted, fontFamily: s.fontFamily }}>/100</span>
        </div>
        <div style={{ width: 240, height: 6, backgroundColor: THEME.card, borderRadius: 3, margin: '16px auto 0', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${barS}%`, background: `linear-gradient(90deg, ${THEME.accent}, ${THEME.accent})`, borderRadius: 3 }} />
        </div>
        <div style={{ fontSize: 12, color: THEME.muted, fontFamily: s.fontFamily, marginTop: 8, opacity: spring({ frame: frame - 20, fps, config: { stiffness: 200, damping: 20 } }) }}>2,450 XP to next level</div>
      </div>
    </AbsoluteFill>
  )
}
