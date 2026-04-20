/**
 * Typography tokens.
 *
 * Font stacks include Noto Sans for Indic scripts and OpenDyslexic for the
 * dyslexia-friendly theme. Line heights are generous by default — important
 * for readers with cognitive differences (WCAG 1.4.12 text spacing).
 *
 * Odia is the reference Indic script. It ships with:
 *   - a dedicated `odia` stack (Noto Sans Oriya first)
 *   - a larger line-height (≥1.7) because matras above and below baseline
 *     plus conjuncts need more vertical breathing room than Latin
 *   - a dyslexia variant that does NOT set letter-spacing, because positive
 *     tracking breaks Odia conjuncts (ନ୍ତ, କ୍ଷ, ଜ୍ଞ); word-spacing is used
 *     instead. See docs/odia-language-strategy.md §3.
 */

const SANS = [
  'Inter',
  '"Noto Sans"',
  '"Noto Sans Devanagari"',
  '"Noto Sans Tamil"',
  '"Noto Sans Bengali"',
  '"Noto Sans Telugu"',
  '"Noto Sans Gujarati"',
  '"Noto Sans Gurmukhi"',
  '"Noto Sans Kannada"',
  '"Noto Sans Malayalam"',
  '"Noto Sans Oriya"',
  'system-ui',
  '-apple-system',
  'Segoe UI',
  'Roboto',
  'sans-serif',
].join(', ');

const ODIA = [
  '"Noto Sans Oriya"',
  '"Lohit Odia"',
  'Shrikhand',
  'Inter',
  'system-ui',
  'sans-serif',
].join(', ');

const MONO = [
  'ui-monospace',
  'SFMono-Regular',
  '"JetBrains Mono"',
  'Menlo',
  'Consolas',
  'monospace',
].join(', ');

const DYSLEXIC = ['"OpenDyslexic"', '"Atkinson Hyperlegible"', SANS].join(', ');

export const fontFamily = {
  sans: SANS,
  odia: ODIA,
  mono: MONO,
  dyslexic: DYSLEXIC,
} as const;

/**
 * Font size scale. Body default is 16px (1rem) — never go below this for
 * running text. 14px is reserved for secondary labels only.
 */
export const fontSize = {
  xs: '0.75rem', // 12px  (labels only, never body)
  sm: '0.875rem', // 14px
  base: '1rem', // 16px
  lg: '1.125rem', // 18px
  xl: '1.25rem', // 20px
  '2xl': '1.5rem', // 24px
  '3xl': '1.875rem', // 30px
  '4xl': '2.25rem', // 36px
  '5xl': '3rem', // 48px
} as const;

/**
 * WCAG 1.4.12 requires line-height >= 1.5 for body text.
 *
 * `odia` and `odiaDyslexic` are Odia-specific: Odia script has matras above
 * and below the baseline plus conjuncts, so comfortable reading needs more
 * vertical space than Latin.
 */
export const lineHeight = {
  tight: 1.2,
  snug: 1.4,
  normal: 1.5,
  relaxed: 1.625,
  odia: 1.7,
  odiaDyslexic: 1.9,
  loose: 2,
} as const;

/**
 * WCAG 1.4.12 requires letter-spacing >= 0.12em adjustable.
 *
 * Do NOT apply the `dyslexic` value to Odia text — positive letter-spacing
 * breaks Odia conjuncts like ନ୍ତ, କ୍ଷ, ଜ୍ଞ. Use `wordSpacing.odiaDyslexic`
 * instead, with `letterSpacing.normal`.
 */
export const letterSpacing = {
  tight: '-0.015em',
  normal: '0',
  wide: '0.025em',
  wider: '0.05em',
  dyslexic: '0.12em',
} as const;

/** Word-spacing exists specifically to support the Odia dyslexia mode. */
export const wordSpacing = {
  normal: 'normal',
  odiaDyslexic: '0.2em',
} as const;

export const fontWeight = {
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;
