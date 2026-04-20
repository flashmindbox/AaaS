module.exports = {
  root: false,
  extends: [require.resolve('@aaas/config/eslint-preset')],
  parserOptions: {
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
  rules: {
    // CLI logging is legitimate here
    'no-console': 'off',
  },
};
