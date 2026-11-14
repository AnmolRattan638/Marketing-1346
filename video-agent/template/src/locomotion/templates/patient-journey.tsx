// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const PatientJourney: React.FC<{ variant?: string }> = ({ variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const steps = [
    { label: 'Book online' },
    { label: 'See doctor' },
    { label: 'Treatment' },
    { label: 'Recovery' },
  ]

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.card }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {steps.map((step, i) => {
          const delay = 8 + i * 14
          const sp = spring({ frame: frame - delay, fps, config: { stiffness: 200, damping: 16 } })
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ textAlign: 'center', opacity: sp, transform: `translateY(${interpolate(sp, [0,1], [12,0])}px)` }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 999, backgroundColor: THEME.bgBottom,
                  border: `${s.borderWidth}px solid ${s.borderColor}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 6px',
                }}>
                  <span style={{ fontSize: 13, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily }}>{i + 1}</span>
                </div>
                <div style={{ fontSize: 11, fontWeight: s.fontWeight, color: THEME.muted, fontFamily: s.fontFamily, width: 70, textAlign: 'center' }}>{step.label}</div>
              </div>
              {i < steps.length - 1 && (
                <div style={{ display: 'flex', gap: 3, alignItems: 'center', opacity: frame > delay + 8 ? 1 : 0.3 }}>
                  {[0, 1, 2, 3, 4].map((d) => (
                    <div key={d} style={{
                      width: 3, height: 3, borderRadius: 999,
                      backgroundColor: frame > delay + 8 ? THEME.text : THEME.cardEdge,
                      opacity: frame > delay + 8 ? interpolate(d, [0, 4], [1, 0.3]) : 0.5,
                    }} />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}
