module.exports = {
  root: false,
  extends: [require.resolve('@aaas/config/eslint-preset')],
  parserOptions: {
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
};
