// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const Changelog: React.FC<{ version?: string; title?: string; features?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  version = 'v2.4.0', title = "What's new", features = 'AI chat assistant,Drag-and-drop timeline,6 style variants,Code export', textColor = THEME.text, bgColor = THEME.card, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')

  const headerS = spring({ frame, fps, config: { stiffness: 200, damping: 18 } })
  const featureList = features.split(',').map((f) => f.trim()).filter(Boolean)

  const isDark = bgColor === THEME.text || bgColor === THEME.text || bgColor === THEME.text
  const textBase = isDark ? THEME.card : textColor
  const textMuted = isDark ? THEME.muted : THEME.muted
  const cardBg = isDark ? THEME.text : THEME.card
  const lineBg = isDark ? THEME.text : THEME.bgBottom

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <div style={{
        width: 560, padding: 44, borderRadius: s.borderRadius + 4,
        backgroundColor: cardBg,
        border: `${s.borderWidth}px solid ${isDark ? THEME.text : s.borderColor}`,
        boxShadow: s.shadow || `0 16px 40px rgba(6,8,13,0.08)`,
        opacity: headerS, transform: `scale(${interpolate(headerS, [0, 1], [0.94, 1])})`,
      }}>
        {/* Version badge */}
        <div style={{
          display: 'inline-block', fontSize: 12, fontWeight: 600,
          color: textColor, backgroundColor: `${textColor}14`,
          padding: '5px 14px', borderRadius: 999, marginBottom: 16,
          fontFamily: 'var(--font-mono)', letterSpacing: '0.03em',
        }}>
          {version}
        </div>

        {/* Title */}
        <h2 style={{
          fontSize: isMono ? 28 : 34, fontWeight: 800, color: textBase,
          fontFamily: s.fontFamily, marginBottom: 28, letterSpacing: s.letterSpacing,
          textTransform: isMono ? 'uppercase' as const : 'none' as const,
        }}>
          {title}
        </h2>

        {/* Feature list */}
        {featureList.map((feature, i) => {
          const delay = 12 + i * 8
          const itemS = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 15 } })
          return (
            <div key={i}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 14, padding: '14px 0',
                opacity: itemS, transform: `translateX(${interpolate(itemS, [0, 1], [-16, 0])}px)`,
              }}>
                {/* Check icon */}
                <div style={{
                  width: 28, height: 28, borderRadius: 999,
                  backgroundColor: textColor, display: 'flex',
                  alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <span style={{ color: THEME.card, fontSize: 14, fontWeight: 700 }}>{'\u2713'}</span>
                </div>
                <span style={{
                  fontSize: 18, fontWeight: 500, color: textBase, fontFamily: s.fontFamily,
                  letterSpacing: s.letterSpacing,
                }}>{feature}</span>
              </div>
              {i < featureList.length - 1 && (
                <div style={{ height: 1, backgroundColor: lineBg, marginLeft: 42 }} />
              )}
            </div>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}
