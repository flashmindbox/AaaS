#!/usr/bin/env node
/**
 * aaas-a11y — audit any URL against WCAG 2.2 AA.
 *
 * Examples:
 *   aaas-a11y https://example.gov.in
 *   aaas-a11y https://example.gov.in --json report.json
 *   aaas-a11y https://example.gov.in --fail-on moderate
 */
import { writeFileSync } from 'node:fs';
import { exit } from 'node:process';

import { Command } from 'commander';
import kleur from 'kleur';
import { chromium } from 'playwright';

import { A11yAuditError, auditPage, type AxeImpact } from './index.js';

const program = new Command();

program
  .name('aaas-a11y')
  .description('WCAG 2.2 AA audit runner for AaaS')
  .argument('<url>', 'URL to audit')
  .option('-j, --json <path>', 'Write full JSON report to path')
  .option(
    '-f, --fail-on <severity>',
    'Severity threshold that fails the run (minor|moderate|serious|critical)',
    'serious',
  )
  .option('-x, --exclude <selector...>', 'CSS selectors to exclude from the scan')
  .option('--timeout <ms>', 'Navigation timeout in ms', '30000')
  .action(async (url: string, opts: CliOptions) => {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    console.info(kleur.dim(`[aaas-a11y] auditing ${url} ...`));
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: Number(opts.timeout) });
      const result = await auditPage(page, {
        exclude: opts.exclude ?? [],
        failOn: opts.failOn as AxeImpact,
      });
      if (opts.json) {
        writeFileSync(opts.json, JSON.stringify(result, null, 2));
        console.info(kleur.dim(`[aaas-a11y] JSON report -> ${opts.json}`));
      }
      console.info(
        kleur.green(
          `PASS  ${url}  passes=${result.passes}  violations=${result.violations.length}  incomplete=${result.incomplete}`,
        ),
      );
    } catch (err) {
      if (err instanceof A11yAuditError) {
        if (opts.json) {
          writeFileSync(opts.json, JSON.stringify(err.result, null, 2));
        }
        console.error(kleur.red(`FAIL  ${url}`));
        for (const v of err.failing) {
          console.error(
            `  ${kleur.red(v.impact ?? 'unknown')}  ${kleur.bold(v.id)}  ${v.help}`,
          );
          for (const n of v.nodes.slice(0, 3)) {
            console.error(`    at ${n.target.join(', ')}`);
          }
          if (v.nodes.length > 3) {
            console.error(kleur.dim(`    ... ${v.nodes.length - 3} more nodes`));
          }
          console.error(kleur.dim(`    ${v.helpUrl}`));
        }
        exit(1);
      }
      throw err;
    } finally {
      await browser.close();
    }
  });

interface CliOptions {
  json?: string;
  failOn?: string;
  exclude?: string[];
  timeout?: string;
}

program.parseAsync(process.argv).catch((err) => {
  console.error(err);
  exit(2);
});
