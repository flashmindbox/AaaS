/**
 * Root ESLint config — provides repo-wide defaults.
 * Packages may extend @aaas/config/eslint-preset for deeper rules.
 */
module.exports = {
  root: true,
  env: {
    node: true,
    es2022: true,
  },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
  extends: ['eslint:recommended'],
  ignorePatterns: [
    'node_modules/',
    'dist/',
    'build/',
    '.next/',
    '.turbo/',
    'coverage/',
    '**/*.d.ts',
  ],
  rules: {
    'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],
    'no-debugger': 'error',
    eqeqeq: ['error', 'always'],
    curly: ['error', 'all'],
  },
};
