import { THEME } from '../graphics/theme'
export interface StyleVariant {
  id: string
  name: string
  description: string
  isFree: boolean
  // Visual overrides passed to compositions
  overrides: {
    borderRadius: number
    fontWeight: number
    shadow: string
    borderWidth: number
    borderColor: string
    bgStyle: 'solid' | 'gradient'
    bgGradient?: string
    letterSpacing: string
    fontFamily: string
  }
}

export const makeVariants = (): StyleVariant[] => [
  {
    id: 'default',
    name: 'Default',
    description: 'Clean and minimal',
    isFree: true,
    overrides: {
      borderRadius: 12,
      fontWeight: 600,
      shadow: 'none',
      borderWidth: 1,
      borderColor: THEME.cardEdge,
      bgStyle: 'solid',
      letterSpacing: '-0.02em',
      fontFamily: 'system-ui, sans-serif',
    },
  },
  {
    id: 'brutalist',
    name: 'Brutalist',
    description: 'Hard edges, thick borders, bold',
    isFree: false,
    overrides: {
      borderRadius: 0,
      fontWeight: 900,
      shadow: `4px 4px 0px ${THEME.text}`,
      borderWidth: 3,
      borderColor: THEME.text,
      bgStyle: 'solid',
      letterSpacing: '0em',
      fontFamily: 'ui-monospace, monospace',
    },
  },
  {
    id: 'rounded',
    name: 'Rounded',
    description: 'Soft corners, friendly feel',
    isFree: false,
    overrides: {
      borderRadius: 24,
      fontWeight: 500,
      shadow: `0 8px 32px rgba(6,8,13,0.08)`,
      borderWidth: 1,
      borderColor: THEME.cardEdge,
      bgStyle: 'solid',
      letterSpacing: '-0.01em',
      fontFamily: 'system-ui, sans-serif',
    },
  },
  {
    id: 'minimal',
    name: 'Minimal',
    description: 'Ultra-clean, whisper-thin',
    isFree: false,
    overrides: {
      borderRadius: 4,
      fontWeight: 400,
      shadow: 'none',
      borderWidth: 0.5,
      borderColor: THEME.bgBottom,
      bgStyle: 'solid',
      letterSpacing: '0.02em',
      fontFamily: 'system-ui, sans-serif',
    },
  },
  {
    id: 'glass',
    name: 'Glass',
    description: 'Frosted glass, translucent layers',
    isFree: false,
    overrides: {
      borderRadius: 16,
      fontWeight: 500,
      shadow: `0 8px 32px rgba(6,8,13,0.06)`,
      borderWidth: 1,
      borderColor: `rgba(232,235,242,0.3)`,
      bgStyle: 'gradient',
      bgGradient: `linear-gradient(135deg, rgba(232,235,242,0.9), rgba(232,235,242,0.6))`,
      letterSpacing: '-0.01em',
      fontFamily: 'system-ui, sans-serif',
    },
  },
  {
    id: 'neo',
    name: 'Neo',
    description: 'Colored shadows, playful offset',
    isFree: false,
    overrides: {
      borderRadius: 14,
      fontWeight: 700,
      shadow: `3px 3px 0px ${THEME.muted}`,
      borderWidth: 2,
      borderColor: THEME.text,
      bgStyle: 'solid',
      letterSpacing: '-0.02em',
      fontFamily: 'system-ui, sans-serif',
    },
  },
]

export function getStyleVariant(id: string): StyleVariant {
  const all = makeVariants()
  return all.find((s) => s.id === id) ?? all[0]
}
