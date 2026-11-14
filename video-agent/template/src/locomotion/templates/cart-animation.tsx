// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const CartAnimation: React.FC<{ title?: string; items?: string; buttonText?: string; textColor?: string; variant?: string }> = ({
  title = 'Your Cart', items: itemsStr = 'Sneakers,T-Shirt,Cap', buttonText = 'Checkout', textColor = THEME.text, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const items = itemsStr.split(',').map((s) => s.trim()).filter(Boolean)

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.card }}>
      <div style={{ width: 520 }}>
        <h3 style={{
          fontSize: isMono ? 22 : 26, fontWeight: s.fontWeight, color: textColor, fontFamily: s.fontFamily,
          marginBottom: 20, opacity: spring({ frame, fps, config: { stiffness: 200, damping: 20 } }),
          letterSpacing: s.letterSpacing,
          textTransform: isMono ? 'uppercase' as const : 'none' as const,
        }}>{title}</h3>
        {items.map((item, i) => {
          const delay = 8 + i * 12
          const sp = spring({ frame: frame - delay, fps, config: { stiffness: 180, damping: 14 } })
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 0', borderBottom: `1px solid ${THEME.bgBottom}`, opacity: sp, transform: `translateX(${interpolate(sp, [0,1], [-30,0])}px)` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{ width: 48, height: 48, borderRadius: s.borderRadius > 16 ? 10 : s.borderRadius, backgroundColor: THEME.bgBottom }} />
                <span style={{ fontSize: 18, fontWeight: 500, color: textColor, fontFamily: s.fontFamily }}>{item}</span>
              </div>
              <span style={{ fontSize: 18, fontWeight: s.fontWeight, color: textColor, fontFamily: s.fontFamily }}>${(29 + i * 20)}</span>
            </div>
          )
        })}
        {(() => { const sp = spring({ frame: frame - 50, fps, config: { stiffness: 200, damping: 16 } }); return (
          <div style={{ marginTop: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: sp }}>
            <span style={{ fontSize: 20, fontWeight: s.fontWeight, color: textColor, fontFamily: s.fontFamily }}>Total: ${items.reduce((sum, _, i) => sum + 29 + i * 20, 0)}</span>
            <div style={{ backgroundColor: textColor, color: THEME.card, padding: '10px 28px', borderRadius: 999, fontSize: 15, fontWeight: s.fontWeight, fontFamily: s.fontFamily, transform: `scale(${sp})` }}>{buttonText}</div>
          </div>
        )})()}
      </div>
    </AbsoluteFill>
  )
}
