/**
 * Motion tokens.
 *
 * All animation durations here must be gated on `prefers-reduced-motion`.
 * Use the `respectReducedMotion()` helper from `../primitives/reduced-motion`.
 */

export const duration = {
  instant: '0ms',
  fast: '120ms',
  base: '200ms',
  slow: '320ms',
  slower: '480ms',
} as const;

export const easing = {
  linear: 'linear',
  standard: 'cubic-bezier(0.2, 0, 0, 1)',
  emphasize: 'cubic-bezier(0.3, 0, 0, 1)',
  decelerate: 'cubic-bezier(0, 0, 0, 1)',
  accelerate: 'cubic-bezier(0.3, 0, 1, 1)',
} as const;
