// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, useCurrentFrame, spring, interpolate, useVideoConfig } from 'remotion'
import { getCompositionStyles } from '../useStyle'

export const StockTicker: React.FC<{ variant?: string }> = ({ variant = 'default' }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)
  const isMono = s.fontFamily.includes('monospace')
  const stocks = [
    { symbol: 'AAPL', price: 189.84, change: +2.4 },
    { symbol: 'GOOGL', price: 141.80, change: +1.1 },
    { symbol: 'TSLA', price: 248.42, change: -0.8 },
  ]

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.bgBottom }}>
      <div style={{ width: 420 }}>
        <h3 style={{
          fontSize: isMono ? 17 : 20, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily,
          marginBottom: 16, opacity: spring({ frame, fps, config: { stiffness: 200, damping: 20 } }),
          letterSpacing: s.letterSpacing,
          textTransform: isMono ? 'uppercase' as const : 'none' as const,
        }}>Market Watch</h3>
        {stocks.map((stock, i) => {
          const delay = 8 + i * 10
          const sp = spring({ frame: frame - delay, fps, config: { stiffness: 200, damping: 16 } })
          const isUp = stock.change > 0
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: `1px solid ${THEME.bgBottom}`, opacity: sp, transform: `translateY(${interpolate(sp, [0,1], [8,0])}px)` }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: THEME.text, fontFamily: s.fontFamily }}>{stock.symbol}</div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 16, fontWeight: s.fontWeight, color: THEME.text, fontFamily: s.fontFamily }}>${stock.price}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: isUp ? THEME.hot : THEME.accent, fontFamily: s.fontFamily }}>{isUp ? '+' : ''}{stock.change}%</div>
              </div>
            </div>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}
