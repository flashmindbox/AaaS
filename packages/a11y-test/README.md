# @aaas/a11y-test

Automated WCAG 2.2 AA test harness for AaaS. Built on Playwright + axe-core.

## Why another wrapper

- **Sane defaults.** Tests against `wcag2a`, `wcag2aa`, `wcag21aa`, `wcag22aa`,
  plus axe best-practice rules, in one call.
- **Typed result shape** suitable for CI artifacts and dashboards.
- **CLI** for one-shot audits of live URLs in CI.
- **WCAG 2.2 checklist** as data (`./checklist`), so we can render coverage
  reports showing which criteria have automated vs manual coverage.

## Programmatic use

```ts
import { chromium } from 'playwright';
import { auditPage } from '@aaas/a11y-test';

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('http://localhost:3000');
const report = await auditPage(page, { failOn: 'serious' });
// auditPage() throws A11yAuditError if any violation >= failOn
await browser.close();
```

## CLI

```bash
pnpm --filter @aaas/a11y-test build
pnpm --filter @aaas/a11y-test exec aaas-a11y https://example.gov.in --json report.json
```

Exit codes:

| Code | Meaning                               |
| ---- | ------------------------------------- |
| 0    | Audit passed at the given threshold   |
| 1    | Violations at or above threshold      |
| 2    | Runner error (network, browser, etc.) |

## What this does NOT cover

Automated tests catch roughly 30% of WCAG issues. Use `manualOnlyCriteria()`
from `./checklist` to render your manual-test worksheet. The bigger gaps:

- Meaningful reading order (SC 1.3.2)
- Screen-reader flow
- Keyboard focus traps (SC 2.1.2)
- Error suggestion quality (SC 3.3.3)
- Motion-actuation (SC 2.5.4)

Our process pairs every automated run with human testing, including at least
one tester from the disability community — see `/docs/wcag-acceptance-checklist.md`.
