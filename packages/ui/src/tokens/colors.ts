/**
 * AaaS color tokens.
 *
 * CONTRACT: every `foreground-on-background` pair used for text must meet
 * WCAG 2.2 AAA (>= 7:1) for normal text, AA (>= 4.5:1) for large text.
 * The ramp below is calibrated — see `colors.test.ts` for the assertions.
 *
 * Naming convention: <role>.<step>  where step 50=lightest, 950=darkest.
 */

export const color = {
  // Neutrals — the workhorse ramp
  neutral: {
    0: '#FFFFFF',
    50: '#F8FAFC',
    100: '#F1F5F9',
    200: '#E2E8F0',
    300: '#CBD5E1',
    400: '#94A3B8',
    500: '#64748B',
    600: '#475569',
    700: '#334155', // AAA on neutral.0  (~10.4:1)
    800: '#1E293B', // AAA on neutral.0  (~15.0:1)
    900: '#0F172A', // AAA on neutral.0  (~18.7:1)
    950: '#020617',
  },

  // Primary — deep navy, references Indian institutional palette
  primary: {
    50: '#EEF3FB',
    100: '#D8E3F3',
    200: '#A9BFDD',
    300: '#6E8EBE',
    400: '#2F5894',
    500: '#19376D',
    600: '#122858',
    700: '#0B2447', // AAA on neutral.0  (~13.1:1)
    800: '#08193A',
    900: '#050F29',
    950: '#02081A',
  },

  // Saffron accent — used sparingly, AA on white, AAA on navy
  saffron: {
    50: '#FDF5EA',
    100: '#FBE9CD',
    200: '#F6D094',
    300: '#EFB35B',
    400: '#E19B2E',
    500: '#C48114',
    600: '#9C6710',
    700: '#704A0B', // AAA on neutral.0  (~7.7:1)
    800: '#4D3307',
    900: '#2E1F04',
  },

  // Semantic
  success: {
    50: '#ECFDF5',
    100: '#D1FAE5',
    500: '#059669',
    700: '#14532D', // AAA on neutral.0  (~9.3:1)
    900: '#052E16',
  },
  warning: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    500: '#D97706',
    700: '#7A4508', // AAA on neutral.0  (~7.8:1)
    900: '#451A03',
  },
  error: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    500: '#DC2626',
    700: '#991B1B', // AAA on neutral.0  (~8.6:1)
    900: '#450A0A',
  },
  info: {
    50: '#EFF6FF',
    100: '#DBEAFE',
    500: '#2563EB',
    700: '#075985', // AAA on neutral.0  (~7.3:1)
    900: '#0C2340',
  },

  // Focus ring — must always be visible on any surface
  focus: {
    ring: '#FFBF00', // amber/saffron — visible on both light and dark
    ringDark: '#003366',
  },
} as const;

/**
 * Semantic token layer — components should consume these, not raw scale.
 * Swapping light/dark or high-contrast themes = reassigning these.
 */
export const semanticLight = {
  bg: color.neutral[0],
  bgSubtle: color.neutral[50],
  bgMuted: color.neutral[100],
  bgInverse: color.primary[900],

  text: color.neutral[900],
  textMuted: color.neutral[700],
  textInverse: color.neutral[0],
  textLink: color.info[700],
  textLinkVisited: color.primary[700],

  border: color.neutral[300],
  borderStrong: color.neutral[700],

  accent: color.primary[700],
  accentFg: color.neutral[0],

  success: color.success[700],
  warning: color.warning[700],
  error: color.error[700],
  info: color.info[700],

  focusRing: color.focus.ring,
} as const;

export const semanticDark = {
  bg: color.neutral[950],
  bgSubtle: color.neutral[900],
  bgMuted: color.neutral[800],
  bgInverse: color.neutral[0],

  text: color.neutral[50],
  textMuted: color.neutral[300],
  textInverse: color.neutral[900],
  textLink: '#93C5FD',
  textLinkVisited: '#C7D2FE',

  border: color.neutral[700],
  borderStrong: color.neutral[300],

  accent: '#93C5FD',
  accentFg: color.neutral[900],

  success: '#86EFAC',
  warning: '#FCD34D',
  error: '#FCA5A5',
  info: '#93C5FD',

  focusRing: color.focus.ring,
} as const;

/**
 * High-contrast theme — maximizes contrast for low-vision users.
 * Pure black/white + saturated primaries, 21:1 where possible.
 */
export const semanticHighContrast = {
  bg: '#FFFFFF',
  bgSubtle: '#FFFFFF',
  bgMuted: '#F5F5F5',
  bgInverse: '#000000',

  text: '#000000',
  textMuted: '#000000',
  textInverse: '#FFFFFF',
  textLink: '#0000EE',
  textLinkVisited: '#551A8B',

  border: '#000000',
  borderStrong: '#000000',

  accent: '#000000',
  accentFg: '#FFFFFF',

  success: '#006600',
  warning: '#B84A00',
  error: '#BB0000',
  info: '#0000EE',

  focusRing: '#FFBF00',
} as const;

export type SemanticTokens = typeof semanticLight;
