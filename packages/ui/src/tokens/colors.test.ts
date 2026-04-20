/**
 * Contrast regression tests.
 *
 * If anyone changes a foreground/background pairing in the semantic layer,
 * these tests catch it before the token ships. Contract: body text pairs
 * must be AAA (>= 7:1). Large text and non-text UI elements may be AA
 * (>= 4.5:1 and >= 3:1 respectively).
 */
import { describe, expect, it } from 'vitest';

import { semanticHighContrast, semanticLight } from './colors';

/** Relative luminance per WCAG. */
function luminance(hex: string): number {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;
  const channel = (c: number) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(fg: string, bg: string): number {
  const lFg = luminance(fg);
  const lBg = luminance(bg);
  const [light, dark] = lFg > lBg ? [lFg, lBg] : [lBg, lFg];
  return (light + 0.05) / (dark + 0.05);
}

describe('semantic light theme — body text AAA contrast', () => {
  it('text on bg is >= 7:1', () => {
    expect(contrast(semanticLight.text, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
  it('textMuted on bg is >= 7:1', () => {
    expect(contrast(semanticLight.textMuted, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
  it('textLink on bg is >= 7:1', () => {
    expect(contrast(semanticLight.textLink, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
  it('accent text on bg is >= 7:1', () => {
    expect(contrast(semanticLight.accent, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
  it('error text on bg is >= 7:1', () => {
    expect(contrast(semanticLight.error, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
  it('success text on bg is >= 7:1', () => {
    expect(contrast(semanticLight.success, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
  it('warning text on bg is >= 7:1', () => {
    expect(contrast(semanticLight.warning, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
  it('info text on bg is >= 7:1', () => {
    expect(contrast(semanticLight.info, semanticLight.bg)).toBeGreaterThanOrEqual(7);
  });
});

describe('semantic light theme — accent button AAA contrast', () => {
  it('accentFg on accent is >= 7:1', () => {
    expect(contrast(semanticLight.accentFg, semanticLight.accent)).toBeGreaterThanOrEqual(7);
  });
});

describe('high-contrast theme', () => {
  it('text on bg is >= 21:1 (pure black on white)', () => {
    expect(contrast(semanticHighContrast.text, semanticHighContrast.bg)).toBeGreaterThan(20);
  });
  it('accentFg on accent is >= 21:1', () => {
    expect(
      contrast(semanticHighContrast.accentFg, semanticHighContrast.accent),
    ).toBeGreaterThan(20);
  });
});
