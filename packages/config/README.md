# @aaas/config

Shared ESLint, TypeScript, and Prettier configs for every package and app.

## Usage

### ESLint

```js
// eslint.config.cjs  (or .eslintrc.cjs)
module.exports = {
  extends: ['@aaas/config/eslint-preset'],
};
```

### TypeScript

```json
// tsconfig.json
{
  "extends": "@aaas/config/tsconfig/library.json",
  "compilerOptions": { "outDir": "dist" },
  "include": ["src/**/*"]
}
```

Available tsconfigs:

| Preset    | Use for                                  |
| --------- | ---------------------------------------- |
| `base`    | Lowest common denominator                |
| `library` | Publishable packages (emits .d.ts, etc.) |
| `node`    | Backend Node services                    |
| `react`   | Next.js / Vite React apps                |

### Prettier

Repo-wide Prettier rules live in `/.prettierrc.json`. This package also
exports the same config as `@aaas/config/prettier` for programmatic use.

## Why these rules

- `jsx-a11y/strict` catches accessibility issues at lint time — this is
  the first line of defence before axe-core tests run.
- `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes` catch the
  bugs that most often break screen-reader flows.
- `import/order` keeps diffs clean in a large monorepo.
