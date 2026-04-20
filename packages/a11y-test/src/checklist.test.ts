import { describe, expect, it } from 'vitest';

import { WCAG_22_CHECKLIST, axeRulesForWcagAA, manualOnlyCriteria } from './checklist';

describe('WCAG 2.2 checklist', () => {
  it('covers all 9 WCAG 2.2 AA-new criteria', () => {
    const ids = WCAG_22_CHECKLIST.map((c) => c.id);
    const newIn22 = ['2.4.11', '2.5.7', '2.5.8', '3.2.6', '3.3.7', '3.3.8'];
    for (const id of newIn22) {
      expect(ids).toContain(id);
    }
  });

  it('has only A and AA entries (AAA is opt-in elsewhere)', () => {
    for (const c of WCAG_22_CHECKLIST) {
      expect(['A', 'AA']).toContain(c.level);
    }
  });

  it('axe rule set is non-empty', () => {
    expect(axeRulesForWcagAA().length).toBeGreaterThan(20);
  });

  it('manual-only criteria list is non-empty (axe does not cover everything)', () => {
    expect(manualOnlyCriteria().length).toBeGreaterThan(0);
  });
});
