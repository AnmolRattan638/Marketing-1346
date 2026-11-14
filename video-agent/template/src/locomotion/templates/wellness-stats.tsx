// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const WellnessStats: React.FC<{ variant?: string }> = ({ variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const stats = [
    { label: 'Heart Rate', value: 72, unit: 'bpm' },
    { label: 'Steps', value: 8432, unit: 'today' },
    { label: 'Sleep', value: 7.5, unit: 'hrs' },
  ]

  const titleS = spring({ frame, fps, config: { stiffness: 200, damping: 20 } })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.card }}>
      <div style={{ width: 440 }}>
        <h3 style={{
          fontSize: isMono ? 19 : 22, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily,
          marginBottom: 20, opacity: titleS, letterSpacing: s.letterSpacing,
          textTransform: isMono ? 'uppercase' as const : 'none' as const,
        }}>Daily Summary</h3>
        <div style={{ display: 'flex', gap: 14 }}>
          {stats.map((stat, i) => {
            const delay = 5 + i * 10
            const sp = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 16 } })
            const count = stat.value > 100 ? Math.round(interpolate(sp, [0,1], [0, stat.value])) : Number((interpolate(sp, [0,1], [0, stat.value])).toFixed(stat.value % 1 ? 1 : 0))
            const barWidth = interpolate(sp, [0, 1], [0, (stat.value / 8432) * 100])

            return (
              <div key={i} style={{
                flex: 1, padding: 18, borderRadius: s.borderRadius,
                border: `${s.borderWidth}px solid ${s.borderColor}`,
                backgroundColor: THEME.bgBottom, opacity: sp, transform: `translateY(${interpolate(sp, [0,1], [10,0])}px)`,
                boxShadow: s.shadow,
              }}>
                <div style={{ fontSize: 11, color: THEME.muted, fontFamily: s.fontFamily, marginBottom: 6 }}>{stat.label}</div>
                <div style={{ fontSize: isMono ? 24 : 28, fontWeight: 800, color: THEME.text, fontFamily: s.fontFamily }}>{count.toLocaleString()}</div>
                <div style={{ fontSize: 10, color: THEME.muted, fontFamily: s.fontFamily, marginBottom: 8 }}>{stat.unit}</div>
                <div style={{ height: 3, backgroundColor: THEME.bgBottom, borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${Math.min(100, barWidth)}%`, backgroundColor: THEME.text, borderRadius: 2 }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </AbsoluteFill>
  )
}
