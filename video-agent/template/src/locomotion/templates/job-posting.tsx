// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const JobPosting: React.FC<{ text?: string; variant?: string }> = ({ text = 'Senior Engineer', variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const cardS = spring({ frame, fps, config: { stiffness: 180, damping: 18 } })
  const tagsS = spring({ frame: frame - 15, fps, config: { stiffness: 200, damping: 18 } })
  const btnS = spring({ frame: frame - 25, fps, config: { stiffness: 200, damping: 14 } })
  const tags = ['Remote', 'Full-time', '$150-200K']

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <div style={{
        width: 380, backgroundColor: THEME.card, borderRadius: s.borderRadius,
        border: `${s.borderWidth}px solid ${s.borderColor}`, padding: 28,
        opacity: cardS, transform: `translateY(${interpolate(cardS, [0,1], [12,0])}px)`,
        boxShadow: s.shadow,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
          <div style={{ width: 40, height: 40, borderRadius: s.borderRadius > 16 ? 10 : s.borderRadius, backgroundColor: THEME.text, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: THEME.card, fontSize: 18, fontWeight: 800, fontFamily: s.fontFamily }}>A</span>
          </div>
          <div>
            <div style={{
              fontSize: isMono ? 15 : 18, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily,
              letterSpacing: s.letterSpacing,
            }}>{text}</div>
            <div style={{ fontSize: 12, color: THEME.muted, fontFamily: s.fontFamily }}>Acme Inc.</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', opacity: tagsS }}>
          {tags.map((t, i) => (
            <span key={i} style={{ fontSize: 11, fontWeight: 500, color: THEME.muted, backgroundColor: THEME.bgBottom, padding: '4px 10px', borderRadius: 999, fontFamily: s.fontFamily }}>{t}</span>
          ))}
        </div>
        <div style={{ marginTop: 16, backgroundColor: THEME.text, color: THEME.card, padding: '10px 0', borderRadius: 999, textAlign: 'center', fontSize: 13, fontWeight: s.fontWeight, fontFamily: s.fontFamily, opacity: btnS, transform: `scale(${btnS})` }}>Apply now</div>
      </div>
    </AbsoluteFill>
  )
}
