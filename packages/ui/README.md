# @aaas/ui

The AaaS accessible design system.

## What's in here

- **Tokens** — colors (WCAG AAA-calibrated), spacing (44px targets),
  typography (Indic + dyslexia-friendly stacks), motion (reduced-motion aware).
- **Primitives** — `Button`, `VisuallyHidden`, `SkipLink`. More coming in Phase 1.
- **Themes** — `light`, `dark`, `hc` (high-contrast), with an orthogonal
  `dyslexia` reading mode toggle.

## Usage

```tsx
import '@aaas/ui/styles.css';
import { Button, SkipLink } from '@aaas/ui';

export function Page() {
  return (
    <>
      <SkipLink href="#main" />
      <main id="main" tabIndex={-1}>
        <Button variant="primary">Continue</Button>
      </main>
    </>
  );
}
```

Apply a theme by setting `data-theme` and (optionally) `data-reading`:

```html
<html data-theme="hc" data-reading="dyslexia">
  ...
</html>
```

## Accessibility contract

1. **Color contrast** — every semantic foreground/background pair used for
   body text meets AAA (>= 7:1). Large text and non-text UI meet AA minimums.
   Enforced by `src/tokens/colors.test.ts`.
2. **Focus** — `:focus-visible` rings are never suppressed; tokens expose
   an amber ring visible on all three themes.
3. **Target size** — interactive controls are >= 44x44 CSS px (WCAG 2.5.8).
4. **Motion** — all animations collapse to 0.01ms when
   `prefers-reduced-motion: reduce` is set.
5. **Axe** — every component has a `jest-axe` test covering typical usage.

## Scripts

```bash
pnpm --filter @aaas/ui build      # tsup ESM+CJS+d.ts
pnpm --filter @aaas/ui test       # vitest incl. axe + contrast
pnpm --filter @aaas/ui typecheck  # strict TS
pnpm --filter @aaas/ui lint       # eslint + jsx-a11y strict
```
