/**
 * Spacing tokens — 4px base grid.
 *
 * WCAG 2.2 "Target Size (Minimum)" (2.5.8) requires 24x24 CSS px minimum
 * for pointer targets. Our default interactive padding resolves to >= 44x44.
 */

export const space = {
  0: '0',
  px: '1px',
  0.5: '0.125rem', // 2px
  1: '0.25rem', // 4px
  1.5: '0.375rem', // 6px
  2: '0.5rem', // 8px
  2.5: '0.625rem', // 10px
  3: '0.75rem', // 12px
  3.5: '0.875rem', // 14px
  4: '1rem', // 16px
  5: '1.25rem', // 20px
  6: '1.5rem', // 24px
  7: '1.75rem', // 28px
  8: '2rem', // 32px
  10: '2.5rem', // 40px
  11: '2.75rem', // 44px  <-- WCAG 2.5.8 target size
  12: '3rem', // 48px
  14: '3.5rem',
  16: '4rem',
  20: '5rem',
  24: '6rem',
  32: '8rem',
} as const;

export const radii = {
  none: '0',
  sm: '0.125rem',
  md: '0.375rem',
  lg: '0.5rem',
  xl: '0.75rem',
  '2xl': '1rem',
  full: '9999px',
} as const;

export const elevation = {
  none: 'none',
  sm: '0 1px 2px rgba(0,0,0,0.08)',
  md: '0 2px 8px rgba(0,0,0,0.12)',
  lg: '0 8px 24px rgba(0,0,0,0.16)',
  focusRing: '0 0 0 3px rgba(255, 191, 0, 0.9)',
} as const;

/** Minimum pointer target size per WCAG 2.2 SC 2.5.8. */
export const MIN_TARGET_SIZE = '44px' as const;
