/**
 * @aaas/a11y-test — programmatic API.
 *
 * Use this from Vitest/Playwright tests to assert that any URL or rendered
 * page meets our WCAG 2.2 AA contract.
 */
import { AxeBuilder } from '@axe-core/playwright';

import type { Page } from 'playwright';

export interface A11yAuditOptions {
  /**
   * WCAG tags to audit against. Defaults to Level A + AA for WCAG 2.2.
   * See https://www.deque.com/axe/core-documentation/api-documentation/#axe-core-tags
   */
  tags?: string[];

  /** CSS selectors to exclude from the scan (iframes, third-party widgets). */
  exclude?: string[];

  /** Specific axe rules to disable, with justification. */
  disableRules?: Array<{ id: string; reason: string }>;

  /**
   * Severity threshold that fails the audit. Anything >= this level causes
   * `auditPage()` to throw. Defaults to `serious` (critical + serious fail).
   */
  failOn?: AxeImpact;
}

export type AxeImpact = 'minor' | 'moderate' | 'serious' | 'critical';

export interface A11yAuditResult {
  url: string;
  passes: number;
  violations: A11yViolation[];
  incomplete: number;
  timestamp: string;
}

export interface A11yViolation {
  id: string;
  impact: AxeImpact | null;
  description: string;
  help: string;
  helpUrl: string;
  nodes: Array<{
    target: string[];
    html: string;
    failureSummary?: string | undefined;
  }>;
}

export const WCAG_22_AA_TAGS = [
  'wcag2a',
  'wcag2aa',
  'wcag21a',
  'wcag21aa',
  'wcag22aa',
  'best-practice',
] as const;

const SEVERITY_RANK: Record<AxeImpact, number> = {
  minor: 1,
  moderate: 2,
  serious: 3,
  critical: 4,
};

/**
 * Run an axe-core audit on an already-navigated Playwright page.
 *
 * Call `page.goto(url)` before invoking this. Throws `A11yAuditError` when
 * any violation meets or exceeds `failOn` (default: serious).
 */
export async function auditPage(
  page: Page,
  options: A11yAuditOptions = {},
): Promise<A11yAuditResult> {
  const tags = options.tags ?? [...WCAG_22_AA_TAGS];
  const failOn = options.failOn ?? 'serious';

  let builder = new AxeBuilder({ page }).withTags(tags);
  for (const selector of options.exclude ?? []) {
    builder = builder.exclude(selector);
  }
  if (options.disableRules?.length) {
    builder = builder.disableRules(options.disableRules.map((r) => r.id));
  }

  const result = await builder.analyze();

  const normalized: A11yAuditResult = {
    url: page.url(),
    passes: result.passes.length,
    incomplete: result.incomplete.length,
    violations: result.violations.map((v) => ({
      id: v.id,
      impact: (v.impact as AxeImpact | undefined) ?? null,
      description: v.description,
      help: v.help,
      helpUrl: v.helpUrl,
      nodes: v.nodes.map((n) => ({
        target: n.target.map((t) => String(t)),
        html: n.html,
        failureSummary: n.failureSummary ?? undefined,
      })),
    })),
    timestamp: new Date().toISOString(),
  };

  const threshold = SEVERITY_RANK[failOn];
  const failing = normalized.violations.filter(
    (v) => v.impact !== null && SEVERITY_RANK[v.impact] >= threshold,
  );
  if (failing.length > 0) {
    throw new A11yAuditError(normalized, failing, failOn);
  }
  return normalized;
}

export class A11yAuditError extends Error {
  readonly result: A11yAuditResult;
  readonly failing: A11yViolation[];
  readonly threshold: AxeImpact;
  constructor(result: A11yAuditResult, failing: A11yViolation[], threshold: AxeImpact) {
    super(
      `A11y audit failed for ${result.url}: ${failing.length} violation(s) at severity >= ${threshold}`,
    );
    this.name = 'A11yAuditError';
    this.result = result;
    this.failing = failing;
    this.threshold = threshold;
  }
}
