// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const BeforeAfter: React.FC<{ beforeTitle?: string; afterTitle?: string; beforeItems?: string; afterItems?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  beforeTitle = 'Before', afterTitle = 'After',
  beforeItems = 'Manual deploys,No monitoring,Slow feedback', afterItems = 'Auto CI/CD,Real-time alerts,Ship in minutes',
  textColor = THEME.text, bgColor = THEME.card, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  const isDark = bgColor === THEME.text || bgColor === THEME.text || bgColor === THEME.text
  const textBase = isDark ? THEME.card : textColor

  const beforeList = beforeItems.split(',').map((i) => i.trim()).filter(Boolean)
  const afterList = afterItems.split(',').map((i) => i.trim()).filter(Boolean)

  // Before card enters first
  const beforeS = spring({ frame: frame - 3, fps, config: { stiffness: 180, damping: 16 } })
  // After card enters with delay
  const afterS = spring({ frame: frame - 20, fps, config: { stiffness: 180, damping: 16 } })
  // Arrow between them
  const arrowS = spring({ frame: frame - 15, fps, config: { stiffness: 200, damping: 14 } })

  const cardStyle = (bg: string, border: string): React.CSSProperties => ({
    width: 300, padding: 32, borderRadius: s.borderRadius,
    backgroundColor: bg,
    border: `${s.borderWidth}px solid ${border}`,
    boxShadow: s.shadow,
  })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        {/* Before */}
        <div style={{
          ...cardStyle(isDark ? THEME.text : THEME.card, isDark ? THEME.text : THEME.cardEdge),
          opacity: beforeS, transform: `translateX(${interpolate(beforeS, [0, 1], [-20, 0])}px)`,
        }}>
          <div style={{
            fontSize: 12, fontWeight: 600, color: THEME.accent,
            textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 16,
            fontFamily: s.fontFamily,
          }}>{beforeTitle}</div>
          {beforeList.map((item, i) => {
            const delay = 8 + i * 6
            const itemS = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 16 } })
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0',
                opacity: itemS, transform: `translateX(${interpolate(itemS, [0, 1], [-10, 0])}px)`,
              }}>
                <span style={{ color: THEME.accent, fontSize: 16 }}>{'\u2717'}</span>
                <span style={{ fontSize: 16, color: isDark ? THEME.muted : THEME.muted, fontFamily: s.fontFamily }}>{item}</span>
              </div>
            )
          })}
        </div>

        {/* Arrow */}
        <div style={{
          fontSize: 32, color: textBase, opacity: arrowS,
          transform: `scale(${arrowS})`,
        }}>{'\u2192'}</div>

        {/* After */}
        <div style={{
          ...cardStyle(isDark ? THEME.text : THEME.card, isDark ? THEME.text : s.borderColor),
          opacity: afterS, transform: `translateX(${interpolate(afterS, [0, 1], [20, 0])}px)`,
          border: `${s.borderWidth + 1}px solid ${textColor}`,
        }}>
          <div style={{
            fontSize: 12, fontWeight: 600, color: textColor,
            textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 16,
            fontFamily: s.fontFamily,
          }}>{afterTitle}</div>
          {afterList.map((item, i) => {
            const delay = 24 + i * 6
            const itemS = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 16 } })
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0',
                opacity: itemS, transform: `translateX(${interpolate(itemS, [0, 1], [10, 0])}px)`,
              }}>
                <span style={{ color: textColor, fontSize: 16 }}>{'\u2713'}</span>
                <span style={{ fontSize: 16, color: textBase, fontWeight: 500, fontFamily: s.fontFamily }}>{item}</span>
              </div>
            )
          })}
        </div>
      </div>
    </AbsoluteFill>
  )
}
