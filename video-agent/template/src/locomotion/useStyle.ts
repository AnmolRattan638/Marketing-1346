import { getStyleVariant } from './styles'

// Returns computed styles for use inside Remotion compositions
// The variant ID is passed as a prop to each composition
export function getCompositionStyles(variantId: string = 'default') {
  const variant = getStyleVariant(variantId)
  const o = variant.overrides

  return {
    variant,
    // Card/container styles
    card: {
      borderRadius: o.borderRadius,
      border: `${o.borderWidth}px solid ${o.borderColor}`,
      boxShadow: o.shadow !== 'none' ? o.shadow : undefined,
      background: o.bgStyle === 'gradient' && o.bgGradient ? o.bgGradient : undefined,
    },
    // Text styles
    text: {
      fontWeight: o.fontWeight,
      letterSpacing: o.letterSpacing,
      fontFamily: o.fontFamily,
    },
    // Shorthand for common patterns
    borderRadius: o.borderRadius,
    fontWeight: o.fontWeight,
    fontFamily: o.fontFamily,
    letterSpacing: o.letterSpacing,
    shadow: o.shadow !== 'none' ? o.shadow : undefined,
    borderWidth: o.borderWidth,
    borderColor: o.borderColor,
  }
}

export type CompositionStyles = ReturnType<typeof getCompositionStyles>
