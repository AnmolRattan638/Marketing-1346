// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const PortfolioBreakdown: React.FC<{ variant?: string }> = ({ variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const segments = [
    { label: 'Stocks', pct: 60, color: THEME.text },
    { label: 'Bonds', pct: 25, color: THEME.muted },
    { label: 'Cash', pct: 15, color: THEME.cardEdge },
  ]

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.card }}>
      <div style={{ width: 440, display: 'flex', gap: 32, alignItems: 'center' }}>
        {/* Donut chart */}
        <svg width={160} height={160} viewBox="0 0 160 160">
          {(() => {
            let offset = 0
            const circumference = 2 * Math.PI * 60
            return segments.map((seg, i) => {
              const delay = 5 + i * 8
              const sp = spring({ frame: frame - delay, fps, config: { stiffness: 140, damping: 16 } })
              const len = (seg.pct / 100) * circumference * sp
              const gap = 4
              const el = <circle key={i} cx={80} cy={80} r={60} fill="none" stroke={seg.color} strokeWidth={20} strokeDasharray={`${Math.max(0, len - gap)} ${circumference}`} strokeDashoffset={-offset} style={{ transform: 'rotate(-90deg)', transformOrigin: '80px 80px' }} />
              offset += (seg.pct / 100) * circumference
              return el
            })
          })()}
        </svg>
        <div>
          {segments.map((seg, i) => {
            const sp = spring({ frame: frame - 10 - i * 6, fps, config: { stiffness: 200, damping: 18 } })
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, opacity: sp }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: seg.color }} />
                <span style={{ fontSize: 14, color: THEME.muted, fontFamily: s.fontFamily }}>{seg.label}</span>
                <span style={{ fontSize: 14, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily, marginLeft: 'auto' }}>{seg.pct}%</span>
              </div>
            )
          })}
        </div>
      </div>
    </AbsoluteFill>
  )
}
