// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const AppFeatureCallout: React.FC<{ text?: string; variant?: string }> = ({ text = 'Real-time collaboration', variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  const screenS = spring({ frame, fps, config: { stiffness: 180, damping: 18 } })
  const badgeS = spring({ frame: frame - 15, fps, config: { stiffness: 250, damping: 14 } })
  const lineS = spring({ frame: frame - 20, fps, config: { stiffness: 200, damping: 16 } })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      {/* App screen mockup */}
      <div style={{
        width: 360, height: 240, backgroundColor: THEME.card, borderRadius: s.borderRadius,
        border: `${s.borderWidth}px solid ${s.borderColor}`, overflow: 'hidden',
        transform: `scale(${screenS})`, opacity: screenS,
        position: 'relative', boxShadow: s.shadow,
      }}>
        {/* Fake toolbar */}
        <div style={{ height: 28, backgroundColor: THEME.bgBottom, borderBottom: `${s.borderWidth}px solid ${s.borderColor}`, display: 'flex', alignItems: 'center', padding: '0 10px', gap: 4 }}>
          <div style={{ width: 6, height: 6, borderRadius: 999, backgroundColor: THEME.cardEdge }} />
          <div style={{ width: 6, height: 6, borderRadius: 999, backgroundColor: THEME.cardEdge }} />
          <div style={{ width: 6, height: 6, borderRadius: 999, backgroundColor: THEME.cardEdge }} />
        </div>
        {/* Content lines */}
        <div style={{ padding: 16 }}>
          {[80, 60, 70, 50].map((w, i) => (
            <div key={i} style={{ height: 8, width: `${w}%`, backgroundColor: THEME.bgBottom, borderRadius: 4, marginBottom: 8 }} />
          ))}
          {/* Highlighted feature area */}
          <div style={{
            height: 40, backgroundColor: THEME.bgBottom, borderRadius: 8, marginTop: 8,
            border: `2px solid ${THEME.text}`,
            opacity: lineS, transform: `scale(${interpolate(lineS, [0, 1], [0.95, 1])})`,
          }} />
        </div>
      </div>

      {/* Callout badge */}
      <div style={{
        position: 'absolute',
        right: 180, top: 160,
        backgroundColor: THEME.text, color: THEME.card,
        padding: '8px 16px', borderRadius: 999,
        fontSize: 14, fontWeight: s.fontWeight, fontFamily: s.fontFamily,
        opacity: badgeS, transform: `scale(${badgeS})`,
        boxShadow: `0 8px 24px rgba(6,8,13,0.15)`,
      }}>
        {text}
      </div>

      {/* Connector line */}
      <div style={{
        position: 'absolute', right: 290, top: 240,
        width: 2, height: interpolate(lineS, [0, 1], [0, 40]),
        backgroundColor: THEME.text,
      }} />
    </AbsoluteFill>
  )
}
