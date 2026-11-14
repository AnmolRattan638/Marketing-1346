// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const SocialPost: React.FC<{ name?: string; handle?: string; text?: string; likes?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  name = 'Acme', handle = '@acmehq', text = 'We just launched! After 6 months of building, our product is live. Check it out and let us know what you think.', likes = '2,847', textColor = THEME.text, bgColor = THEME.bgBottom, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  const cardS = spring({ frame: frame - 2, fps, config: { stiffness: 180, damping: 16 } })
  const textS = spring({ frame: frame - 10, fps, config: { stiffness: 160, damping: 18 } })
  const metricsS = spring({ frame: frame - 25, fps, config: { stiffness: 200, damping: 14 } })
  const heartS = spring({ frame: frame - 35, fps, config: { stiffness: 300, damping: 10 } })

  const isDark = bgColor === THEME.text || bgColor === THEME.text || bgColor === THEME.text
  const cardBg = isDark ? THEME.text : THEME.card
  const textBase = isDark ? THEME.card : textColor
  const textMuted = isDark ? THEME.muted : THEME.muted

  const likesNum = parseInt(likes.replace(/,/g, ''), 10) || 0
  const animatedLikes = Math.round(interpolate(metricsS, [0, 1], [0, likesNum]))

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <div style={{
        width: 560, padding: 32, borderRadius: s.borderRadius + 4,
        backgroundColor: cardBg,
        border: `${s.borderWidth}px solid ${isDark ? THEME.text : s.borderColor}`,
        boxShadow: s.shadow || `0 12px 32px rgba(6,8,13,0.08)`,
        opacity: cardS, transform: `scale(${interpolate(cardS, [0, 1], [0.92, 1])})`,
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 999,
            backgroundColor: textColor, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            fontSize: 20, fontWeight: 700, color: cardBg, fontFamily: s.fontFamily,
          }}>
            {name.charAt(0)}
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: textBase, fontFamily: s.fontFamily }}>{name}</div>
            <div style={{ fontSize: 14, color: textMuted, fontFamily: s.fontFamily }}>{handle}</div>
          </div>
        </div>

        {/* Post text */}
        <p style={{
          fontSize: 20, lineHeight: 1.6, color: textBase, fontFamily: s.fontFamily,
          marginBottom: 24, opacity: textS,
          transform: `translateY(${interpolate(textS, [0, 1], [8, 0])}px)`,
        }}>
          {text}
        </p>

        {/* Metrics row */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 24,
          paddingTop: 16, borderTop: `1px solid ${isDark ? THEME.text : THEME.bgBottom}`,
          opacity: metricsS,
        }}>
          {/* Heart */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              fontSize: 18, color: THEME.accent,
              transform: `scale(${1 + (heartS > 0.8 ? (1 - heartS) * 3 : 0)})`,
            }}>{'\u2764'}</span>
            <span style={{ fontSize: 15, fontWeight: 600, color: textMuted, fontFamily: s.fontFamily }}>
              {animatedLikes.toLocaleString()}
            </span>
          </div>
          {/* Retweet */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 16, color: textMuted }}>{'\uD83D\uDD01'}</span>
            <span style={{ fontSize: 15, color: textMuted, fontFamily: s.fontFamily }}>
              {Math.round(likesNum * 0.3).toLocaleString()}
            </span>
          </div>
          {/* Views */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 16, color: textMuted }}>{'\uD83D\uDC41'}</span>
            <span style={{ fontSize: 15, color: textMuted, fontFamily: s.fontFamily }}>
              {(likesNum * 12).toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  )
}
