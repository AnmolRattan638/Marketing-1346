// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const StatsDashboard: React.FC<{ labels?: string; values?: string; textColor?: string; variant?: string }> = ({
  labels: labelsStr = 'Users,Revenue,Growth,NPS', values: valuesStr = '12847,$84K,127%,72', textColor = THEME.text, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')

  const labelList = labelsStr.split(',').map((s) => s.trim())
  const valueList = valuesStr.split(',').map((s) => s.trim())
  const stats = labelList.map((label, i) => {
    const raw = valueList[i] ?? '0'
    const prefix = raw.startsWith('$') ? '$' : ''
    const suffix = raw.endsWith('%') ? '%' : raw.endsWith('K') ? 'K' : ''
    const num = parseInt(raw.replace(/[^0-9]/g, ''), 10) || 0
    return { label, value: num, prefix, suffix }
  })

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, width: 620 }}>
        {stats.map((stat, i) => {
          const delay = 5 + i * 8
          const sp = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 16 } })
          const count = Math.round(interpolate(sp, [0, 1], [0, stat.value]))

          return (
            <div key={i} style={{
              backgroundColor: THEME.card, borderRadius: s.borderRadius, padding: '28px 32px',
              border: `${s.borderWidth}px solid ${s.borderColor}`, opacity: sp,
              transform: `scale(${interpolate(sp, [0, 1], [0.95, 1])})`,
              boxShadow: s.shadow,
            }}>
              <div style={{ fontSize: 14, color: THEME.muted, fontFamily: s.fontFamily, marginBottom: 6 }}>{stat.label}</div>
              <div style={{
                fontSize: isMono ? 36 : 44, fontWeight: 800, color: textColor, fontFamily: s.fontFamily,
                letterSpacing: s.letterSpacing,
              }}>
                {stat.prefix}{count.toLocaleString()}{stat.suffix}
              </div>
            </div>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}
