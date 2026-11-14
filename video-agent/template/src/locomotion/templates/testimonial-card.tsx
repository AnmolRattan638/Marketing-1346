// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.
import React from 'react'
import { THEME } from '../../graphics/theme'
import { AbsoluteFill, spring, interpolate, useVideoConfig } from 'remotion'
import { useCurrentFrame } from '../timewarp'
import { getCompositionStyles } from '../useStyle'

export const TestimonialCard: React.FC<{ quote?: string; name?: string; role?: string; textColor?: string; bgColor?: string; variant?: string }> = ({
  quote = 'This product completely changed how we work. The team shipped 3x faster in the first month.',
  name = 'Sarah Chen', role = 'CTO at Acme', textColor = THEME.text, bgColor = THEME.bgBottom, variant = 'default',
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const s = getCompositionStyles(variant)

  const cardS = spring({ frame: frame - 3, fps, config: { stiffness: 160, damping: 16 } })
  const quoteS = spring({ frame: frame - 12, fps, config: { stiffness: 140, damping: 18 } })
  const avatarS = spring({ frame: frame - 25, fps, config: { stiffness: 200, damping: 14 } })
  const nameS = spring({ frame: frame - 30, fps, config: { stiffness: 180, damping: 16 } })

  const isDark = bgColor === THEME.text || bgColor === THEME.text || bgColor === THEME.text
  const cardBg = isDark ? THEME.text : THEME.card
  const borderCol = isDark ? THEME.text : s.borderColor

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: bgColor }}>
      <div style={{
        width: 620, padding: 48, borderRadius: s.borderRadius + 4,
        backgroundColor: cardBg,
        border: `${s.borderWidth}px solid ${borderCol}`,
        boxShadow: isDark ? `0 24px 48px rgba(6,8,13,0.4)` : (s.shadow || `0 24px 48px rgba(6,8,13,0.08)`),
        opacity: cardS, transform: `scale(${interpolate(cardS, [0, 1], [0.92, 1])})`,
        backdropFilter: 'blur(20px)',
      }}>
        {/* Quote mark */}
        <div style={{
          fontSize: 64, lineHeight: 1, color: textColor, opacity: 0.15,
          fontFamily: 'Georgia, serif', marginBottom: -20,
        }}>{'\u201C'}</div>

        {/* Quote text */}
        <p style={{
          fontSize: 22, lineHeight: 1.6, color: textColor, fontFamily: s.fontFamily,
          fontWeight: 500, marginBottom: 32,
          opacity: quoteS, transform: `translateY(${interpolate(quoteS, [0, 1], [10, 0])}px)`,
          letterSpacing: s.letterSpacing,
        }}>
          {quote}
        </p>

        {/* Author */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {/* Avatar circle */}
          <div style={{
            width: 48, height: 48, borderRadius: 999,
            backgroundColor: textColor, opacity: avatarS,
            transform: `scale(${avatarS})`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 20, fontWeight: 700, color: cardBg, fontFamily: s.fontFamily,
          }}>
            {name.charAt(0)}
          </div>
          <div style={{ opacity: nameS, transform: `translateX(${interpolate(nameS, [0, 1], [-8, 0])}px)` }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: textColor, fontFamily: s.fontFamily }}>{name}</div>
            <div style={{ fontSize: 14, color: isDark ? THEME.muted : THEME.muted, fontFamily: s.fontFamily }}>{role}</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  )
}
