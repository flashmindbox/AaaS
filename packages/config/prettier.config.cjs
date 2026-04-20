/**
 * @aaas/config/prettier
 *
 * Shared Prettier config. Mirrors root .prettierrc.json — the CJS export
 * lets packages import it programmatically when they need to.
 */
module.exports = {
  semi: true,
  singleQuote: true,
  trailingComma: 'all',
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,
  arrowParens: 'always',
  bracketSpacing: true,
  endOfLine: 'lf',
};
