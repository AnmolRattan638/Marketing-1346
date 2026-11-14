// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const ScreenShowcase: React.FC<{ title?: string; features?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  title = 'Dashboard', features = 'Real-time analytics,Team collaboration,Custom reports', textColor = THEME.text, bgColor = THEME.bgBottom, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  const browserS = spring({ frame: frame - 2, fps, config: { stiffness: 160, damping: 16 } })
  const featureList = features.split(',').map((f) => f.trim()).filter(Boolean)

  const isDark = bgColor === THEME.text || bgColor === THEME.text || bgColor === THEME.text
  const chromeBg = isDark ? THEME.text : THEME.card
  const uiBg = isDark ? THEME.text : THEME.bgBottom

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <div style={{ display: 'flex', gap: 32, alignItems: 'center' }}>
        {/* Browser mockup */}
        <div style={{
          width: 480, borderRadius: s.borderRadius + 4, overflow: 'hidden',
          border: `${s.borderWidth}px solid ${isDark ? THEME.text : s.borderColor}`,
          boxShadow: s.shadow || `0 16px 40px rgba(6,8,13,0.1)`,
          opacity: browserS, transform: `translateX(${interpolate(browserS, [0, 1], [-20, 0])}px)`,
        }}>
          {/* Chrome bar */}
          <div style={{
            height: 36, backgroundColor: isDark ? THEME.text : THEME.bgBottom,
            display: 'flex', alignItems: 'center', padding: '0 14px', gap: 7,
            borderBottom: `1px solid ${isDark ? THEME.text : THEME.cardEdge}`,
          }}>
            <div style={{ width: 10, height: 10, borderRadius: 999, backgroundColor: THEME.accent }} />
            <div style={{ width: 10, height: 10, borderRadius: 999, backgroundColor: THEME.accent }} />
            <div style={{ width: 10, height: 10, borderRadius: 999, backgroundColor: THEME.hot }} />
            <div style={{
              marginLeft: 16, flex: 1, height: 20, borderRadius: 4,
              backgroundColor: isDark ? THEME.text : THEME.cardEdge, maxWidth: 200,
            }} />
          </div>

          {/* App UI */}
          <div style={{ backgroundColor: chromeBg, padding: 24, minHeight: 260 }}>
            {/* Nav placeholder */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
              {[80, 60, 70].map((w, i) => (
                <div key={i} style={{ width: w, height: 8, borderRadius: 4, backgroundColor: uiBg }} />
              ))}
            </div>
            {/* Title */}
            <div style={{ fontSize: 20, fontWeight: 700, color: isDark ? THEME.card : textColor, fontFamily: s.fontFamily, marginBottom: 16 }}>{title}</div>
            {/* Fake cards grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {[0, 1, 2, 3].map((i) => {
                const delay = 15 + i * 6
                const cS = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 14 } })
                return (
                  <div key={i} style={{
                    height: 60, borderRadius: s.borderRadius / 2,
                    backgroundColor: uiBg, opacity: cS,
                    border: `1px solid ${isDark ? THEME.text : THEME.cardEdge}`,
                  }} />
                )
              })}
            </div>
          </div>
        </div>

        {/* Feature callouts */}
        <div style={{ maxWidth: 260 }}>
          {featureList.map((feature, i) => {
            const delay = 20 + i * 10
            const fS = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 16 } })
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20,
                opacity: fS, transform: `translateX(${interpolate(fS, [0, 1], [16, 0])}px)`,
              }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 999, backgroundColor: `${textColor}14`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  fontSize: 14, color: textColor, fontWeight: 700,
                }}>{i + 1}</div>
                <span style={{
                  fontSize: 16, fontWeight: 600, color: isDark ? THEME.card : textColor, fontFamily: s.fontFamily,
                }}>{feature}</span>
              </div>
            )
          })}
        </div>
      </div>
    </AbsoluteFill>
  )
}
