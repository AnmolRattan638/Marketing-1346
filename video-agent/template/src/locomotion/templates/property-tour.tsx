// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const PropertyTour: React.FC<{ text?: string; variant?: string }> = ({ text = '42 Oak Avenue', variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const imgS = spring({ frame, fps, config: { stiffness: 160, damping: 18 } })
  const infoS = spring({ frame: frame - 15, fps, config: { stiffness: 200, damping: 18 } })
  const zoom = interpolate(frame, [0, 90], [1, 1.06], { extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <div style={{
        width: 440, overflow: 'hidden', borderRadius: s.borderRadius,
        border: `${s.borderWidth}px solid ${s.borderColor}`, boxShadow: s.shadow,
      }}>
        <div style={{ height: 200, backgroundColor: THEME.bgBottom, overflow: 'hidden', opacity: imgS }}>
          <div style={{ width: '100%', height: '100%', background: `linear-gradient(135deg, ${THEME.cardEdge} 0%, ${THEME.cardEdge} 100%)`, transform: `scale(${zoom})` }} />
        </div>
        <div style={{ padding: 20, backgroundColor: THEME.card, opacity: infoS, transform: `translateY(${interpolate(infoS, [0,1], [8,0])}px)` }}>
          <h3 style={{
            fontSize: isMono ? 17 : 20, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily,
            letterSpacing: s.letterSpacing,
          }}>{text}</h3>
          <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
            {['3 bed', '2 bath', '1,850 sqft'].map((f, i) => (
              <span key={i} style={{ fontSize: 12, color: THEME.muted, fontFamily: s.fontFamily }}>{f}</span>
            ))}
          </div>
          <div style={{ fontSize: isMono ? 20 : 24, fontWeight: 800, color: THEME.text, fontFamily: s.fontFamily, marginTop: 10 }}>$485,000</div>
        </div>
      </div>
    </AbsoluteFill>
  )
}
