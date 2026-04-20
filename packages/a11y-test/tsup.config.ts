import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts', 'src/checklist.ts', 'src/cli.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  sourcemap: true,
  clean: true,
  target: 'node20',
  splitting: false,
  banner: (ctx) => (ctx.format === 'esm' ? { js: '#!/usr/bin/env node' } : {}),
});
