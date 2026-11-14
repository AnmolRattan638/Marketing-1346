// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const LessonIntro: React.FC<{ text?: string; variant?: string }> = ({ text = 'Lesson 3: Variables', variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const numS = spring({ frame, fps, config: { stiffness: 200, damping: 14 } })
  const titleS = spring({ frame: frame - 10, fps, config: { stiffness: 180, damping: 18 } })
  const barS = interpolate(frame, [15, 40], [0, 100], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ width: 56, height: 56, borderRadius: s.borderRadius, backgroundColor: THEME.text, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', transform: `scale(${numS})` }}>
          <span style={{ color: THEME.card, fontSize: 22, fontWeight: 800, fontFamily: s.fontFamily }}>3</span>
        </div>
        <h1 style={{
          fontSize: isMono ? 30 : 36, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily,
          opacity: titleS, transform: `translateY(${interpolate(titleS, [0,1], [10,0])}px)`,
          letterSpacing: s.letterSpacing,
          textTransform: isMono ? 'uppercase' as const : 'none' as const,
        }}>{text}</h1>
        <div style={{ width: 200, height: 3, backgroundColor: THEME.cardEdge, borderRadius: 2, margin: '16px auto 0', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${barS}%`, backgroundColor: THEME.text, borderRadius: 2 }} />
        </div>
        <div style={{ fontSize: 12, color: THEME.muted, marginTop: 8, fontFamily: s.fontFamily, opacity: spring({ frame: frame - 20, fps, config: { stiffness: 200, damping: 20 } }) }}>12 min read</div>
      </div>
    </AbsoluteFill>
  )
}
