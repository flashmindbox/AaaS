# @aaas/ui bundled fonts

AaaS deployments are expected to run on-prem at institutions where Google Fonts CDN access is either slow, blocked, or non-compliant with data-flow rules. This folder is the self-hosted font origin.

## What to drop in

| File | Source | Licence | Why we ship it |
|---|---|---|---|
| `NotoSansOriya-Regular.woff2` | notofonts.github.io/oriya | OFL 1.1 | Primary Odia body text |
| `NotoSansOriya-SemiBold.woff2` | same | OFL 1.1 | Odia headings/buttons |
| `NotoSansOriya-Bold.woff2` | same | OFL 1.1 | Strong emphasis in Odia |
| `Inter-Variable.woff2` | rsms.me/inter | OFL 1.1 | Latin base face |
| `OpenDyslexic-Regular.woff2` | opendyslexic.org | Bespoke (free for use) | Latin dyslexia mode |

Place the binaries directly in this folder. The `.woff2` filenames above are what `styles.css` `@font-face` rules expect.

## How the CSS finds them

Fonts are loaded from `@aaas/ui/dist/fonts/` at runtime. A tsup copy step (planned in Phase 1, alongside the binary drop-in) will mirror this folder into `dist/fonts/`. Apps import the CSS once:

```ts
import '@aaas/ui/styles.css';
```

…and the browser resolves `url('./fonts/NotoSansOriya-Regular.woff2')` relative to the stylesheet's location.

## Why the binaries are not checked in

- Font files are large (Noto Sans Oriya alone is ~100 KB per weight).
- Licence terms require shipping the OFL/licence file alongside the font, which adds noise to the git tree.
- Different institutions may want to swap in their own licensed faces (e.g. a paid Odia corporate display face).

Fetch + verify once per environment:

```bash
# From the repo root
pnpm --filter @aaas/ui run fetch-fonts
```

That script (to be added in Phase 1) downloads the expected files and verifies their SHA-256 against `fonts.lock.json`.

## Fallback behaviour today

Until the binaries are dropped in, the CSS stack falls back through the system Noto Sans Oriya (common on modern Linux and recent Android), then Lohit Odia (Fedora/Debian), then Shrikhand (display-only, shape-incorrect for body text but readable), then Inter (Latin fallback — Odia glyphs render as tofu). The assistive widget degrades gracefully; it does not break.

This is acceptable for Phase 0 demo-on-a-laptop. It is **not** acceptable for a pilot deployment — drop the files in before going live.
