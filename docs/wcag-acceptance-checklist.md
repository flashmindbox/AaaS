# WCAG 2.2 AA Acceptance Checklist

**What this is:** the human-readable counterpart to
`packages/a11y-test/src/checklist.ts`. The `.ts` file is what CI enforces
automatically. This doc is what a reviewer, PM, or external auditor uses
when accepting a piece of work as "accessible enough to ship".

**Scope:** every AaaS-owned surface — the widget, the dashboard, the exam
app, the mobile app, the kiosk, and any demo site we publish. External
tenant sites are a separate matter — we offer them an audit tool, not a
compliance guarantee.

**Target level:** WCAG 2.2, Level AA, end to end. AAA where the team
explicitly commits (currently: color contrast, which we hold at AAA in
`@aaas/ui`).

**How to use this checklist:**

- Every PR checks in **automated** coverage (axe-core + jest-axe + the
  unit tests per package).
- Every milestone review does a **manual** pass — the items marked
  "Manual" below must be walked through with actual assistive tech (AT).
- For the exam app and the kiosk, an **AT user review** is required
  before ship (i.e. a user who actually relies on AT runs the flow).

Columns:

| Col | Meaning                                                         |
| --- | --------------------------------------------------------------- |
| ID  | WCAG 2.2 success criterion number                               |
| Lvl | A / AA                                                          |
| Cov | **Auto** = axe catches it / **Manual** = human check / **Mix**  |
| Tool| The primary way we verify                                       |

---

## 1. Perceivable

### 1.1.1 Non-text Content (A) — Auto
**Tool:** axe (`image-alt`, `input-image-alt`, `area-alt`, `svg-img-alt`).
**Definition of done:** every `<img>`, `<svg>`, `<area>`, `<input type="image">`
has a meaningful text alternative, or `alt=""` / `aria-hidden="true"` when
genuinely decorative.

### 1.2.1 Audio-only / Video-only (Prerecorded) (A) — Manual
**Tool:** content review.
**Done:** transcripts published for audio-only; text description or audio
track for video-only.

### 1.2.2 Captions (Prerecorded) (A) — Auto (partial)
**Tool:** axe (`video-caption`) + manual quality review.
**Done:** every prerecorded video has captions; captions are accurate,
synchronized, and identify speakers.

### 1.2.3 Audio Description or Media Alternative (A) — Manual
**Done:** AD track OR an equivalent text alternative is available.

### 1.2.4 Captions (Live) (AA) — Manual
**Done:** live broadcasts have captions within industry-standard latency.
On AaaS this applies to live-streamed announcements and the future
sign-language avatar.

### 1.2.5 Audio Description (Prerecorded) (AA) — Manual
**Done:** AD track on all prerecorded video that has important visual info
not otherwise described.

### 1.3.1 Info and Relationships (A) — Auto
**Tool:** axe (`list`, `listitem`, `definition-list`, `dlitem`, `label`,
`th-has-data-cells`, `td-headers-attr`).
**Done:** structure is conveyed semantically (headings, lists, table
headers) — not through visual styling alone.

### 1.3.2 Meaningful Sequence (A) — Manual
**Done:** reading order matches logical order; DOM order is sensible
even with CSS disabled.

### 1.3.3 Sensory Characteristics (A) — Manual
**Done:** instructions do not rely on shape, size, location, or color
alone (e.g. never just "click the red button on the right").

### 1.3.4 Orientation (AA) — Auto (partial)
**Tool:** axe (`css-orientation-lock`).
**Done:** content works in both portrait and landscape; no forced
orientation except where essential (camera scan).

### 1.3.5 Identify Input Purpose (AA) — Auto
**Tool:** axe (`autocomplete-valid`).
**Done:** form inputs that collect user info use appropriate
`autocomplete` tokens (name, email, tel, etc.).

### 1.4.1 Use of Color (A) — Mix
**Tool:** axe (`link-in-text-block`) + manual review.
**Done:** color is never the only means of conveying information.
Required fields, errors, and states have a secondary indicator (icon,
text, underline, shape).

### 1.4.2 Audio Control (A) — Auto
**Tool:** axe (`no-autoplay-audio`).
**Done:** no autoplay audio longer than 3 s without a dedicated control.

### 1.4.3 Contrast (Minimum) (AA) — Auto
**Tool:** axe (`color-contrast`).
**Done:** 4.5:1 for body text, 3:1 for large text.
**AaaS commitment:** our `@aaas/ui` tokens hold body text at **7:1 AAA**
by default. Contrast regressions are caught by `colors.test.ts` and
fail CI.

### 1.4.4 Resize Text (AA) — Auto (partial)
**Tool:** axe (`meta-viewport`).
**Done:** text zoom to 200% does not break layout or hide content.
No `user-scalable=no`.

### 1.4.5 Images of Text (AA) — Manual
**Done:** real text is used instead of images of text, except for logos.

### 1.4.10 Reflow (AA) — Manual
**Done:** content fits at 320 CSS px wide (or 256 CSS px for vertical
text) without two-dimensional scrolling.

### 1.4.11 Non-text Contrast (AA) — Auto
**Tool:** axe (`color-contrast-enhanced`).
**Done:** UI components and graphical objects have 3:1 contrast against
adjacent colors.

### 1.4.12 Text Spacing (AA) — Manual
**Done:** with line-height 1.5x, paragraph spacing 2x, letter spacing
0.12em, word spacing 0.16em, no content is lost or cut off. `@aaas/ui`
tokens ship with line-height 1.5 by default.

### 1.4.13 Content on Hover or Focus (AA) — Manual
**Done:** hover/focus-triggered popups are **dismissable** (Esc),
**hoverable** (can move mouse onto them), and **persistent** (stay until
dismissed or condition no longer applies).

---

## 2. Operable

### 2.1.1 Keyboard (A) — Mix
**Tool:** axe (`scrollable-region-focusable`) + manual walkthrough.
**Done:** every function is reachable and usable with keyboard only.
No mouse-only actions.

### 2.1.2 No Keyboard Trap (A) — Manual
**Done:** focus can leave any component via standard keys (Tab, Esc).
Testing: Tab through the whole app; you should always be able to get out.

### 2.1.4 Character Key Shortcuts (A) — Manual
**Done:** any single-character shortcut is either remappable, turn-off-able,
or only active when focus is on a specific component.

### 2.2.1 Timing Adjustable (A) — Manual
**Done:** no time limits, or the user can extend to at least 10x or
disable; exam accommodations apply here (extra time per candidate profile).

### 2.2.2 Pause, Stop, Hide (A) — Auto (partial)
**Tool:** axe (`meta-refresh`).
**Done:** moving, blinking, scrolling content can be paused or stopped;
no auto-refreshing pages.

### 2.3.1 Three Flashes or Below Threshold (A) — Manual
**Done:** no content flashes more than 3x/sec above the WCAG threshold.
Strongly avoided entirely.

### 2.4.1 Bypass Blocks (A) — Auto
**Tool:** axe (`bypass`, `skip-link`).
**Done:** skip link is the first focusable element on every page.
`@aaas/ui` ships `<SkipLink />`.

### 2.4.2 Page Titled (A) — Auto
**Tool:** axe (`document-title`).
**Done:** every route / screen has a descriptive `<title>`.

### 2.4.3 Focus Order (A) — Auto
**Tool:** axe (`tabindex`).
**Done:** focus follows logical order; no positive `tabindex` values.

### 2.4.4 Link Purpose (In Context) (A) — Auto
**Tool:** axe (`link-name`).
**Done:** link text (or surrounding context) makes the destination clear.
No "click here".

### 2.4.5 Multiple Ways (AA) — Manual
**Done:** at least two of: nav menu, search, sitemap, breadcrumb.

### 2.4.6 Headings and Labels (AA) — Auto
**Tool:** axe (`empty-heading`, `heading-order`).
**Done:** headings and labels are descriptive; no empty headings; no
skipped heading levels without reason.

### 2.4.7 Focus Visible (AA) — Mix
**Tool:** axe (`focus-order-semantics`) + manual visual review.
**Done:** focus indicator is visible on every control. `@aaas/ui` enforces
a 3px amber ring via `:focus-visible` at the token layer — do not override.

### 2.4.11 Focus Not Obscured (Minimum) (AA, new in 2.2) — Manual
**Done:** the focused element is not entirely hidden by sticky headers,
footers, banners, or author content.

### 2.5.1 Pointer Gestures (A) — Manual
**Done:** any multi-point or path-based gesture has a single-point
alternative (tap, click).

### 2.5.2 Pointer Cancellation (A) — Manual
**Done:** actions trigger on `up-event`, not `down-event`; users can
abort a press by moving off before release.

### 2.5.3 Label in Name (A) — Auto
**Tool:** axe (`label-content-name-mismatch`).
**Done:** the visible label text is part of the accessible name (so voice
control users can say what they see).

### 2.5.4 Motion Actuation (A) — Manual
**Done:** any feature triggered by device motion (shake, tilt) has a UI
alternative and can be turned off.

### 2.5.7 Dragging Movements (AA, new in 2.2) — Manual
**Done:** any drag-to-rearrange has a single-pointer alternative (arrow
buttons, etc.).

### 2.5.8 Target Size (Minimum) (AA, new in 2.2) — Auto
**Tool:** axe (`target-size`).
**Done:** pointer targets are at least 24x24 CSS px. `@aaas/ui` buttons
ship at 44x44 by default.

---

## 3. Understandable

### 3.1.1 Language of Page (A) — Auto
**Tool:** axe (`html-has-lang`, `html-lang-valid`).
**Done:** every page has a valid `<html lang="...">`.

### 3.1.2 Language of Parts (AA) — Auto
**Tool:** axe (`valid-lang`).
**Done:** inline language changes marked with `lang` attribute.

### 3.2.1 On Focus (A) — Manual
**Done:** moving focus to a component does not cause a context change
(no auto-submitting, no opening modals).

### 3.2.2 On Input (A) — Manual
**Done:** changing an input's value does not cause a context change
unless the user has been warned.

### 3.2.3 Consistent Navigation (AA) — Manual
**Done:** nav appears in the same place, same order, across the site.

### 3.2.4 Consistent Identification (AA) — Manual
**Done:** components that do the same thing are labeled the same.

### 3.2.6 Consistent Help (A, new in 2.2) — Manual
**Done:** help mechanisms (contact, FAQ, chat) appear in the same
relative order on every page.

### 3.3.1 Error Identification (A) — Auto (partial)
**Tool:** axe (`aria-valid-attr-value`).
**Done:** form errors are identified in text and associated with the
field (aria-describedby).

### 3.3.2 Labels or Instructions (A) — Auto
**Tool:** axe (`label`, `form-field-multiple-labels`).
**Done:** every input has a visible label or clear instructions.

### 3.3.3 Error Suggestion (AA) — Manual
**Done:** when we know how to fix an error, we say so.

### 3.3.4 Error Prevention (Legal/Financial/Data) (AA) — Manual
**Done:** for consequential actions (exam submit, account delete,
payment) the user can review and confirm, or undo.

### 3.3.7 Redundant Entry (A, new in 2.2) — Manual
**Done:** previously-entered info is not asked for again in the same
session unless essential.

### 3.3.8 Accessible Authentication (Minimum) (AA, new in 2.2) — Manual
**Done:** authentication does not require a cognitive function test
(remembering, transcribing, solving puzzles) unless an alternative is
offered — e.g., we support magic links / SSO / passkeys, not only
password+captcha.

---

## 4. Robust

### 4.1.2 Name, Role, Value (A) — Auto
**Tool:** axe (`aria-allowed-attr`, `aria-required-attr`, `aria-roles`,
`aria-valid-attr`, `button-name`).
**Done:** every interactive element exposes a name, role, and current
value/state to AT.

### 4.1.3 Status Messages (AA) — Auto (partial)
**Tool:** axe (`aria-live-region-ids`).
**Done:** non-blocking status updates (toasts, form saves) reach AT
without moving focus (use `role="status"` or `aria-live`).

---

## 5. AaaS-specific addenda (stricter than WCAG)

We commit to the following beyond the WCAG floor:

1. **Body-text contrast AAA (>= 7:1).** Enforced by `@aaas/ui` tokens.
2. **Minimum target size 44x44.** `@aaas/ui` primitives default to this.
3. **Reduced motion.** All animations collapse to 0.01ms under
   `prefers-reduced-motion: reduce`.
4. **First-focusable is always a skip link** in every app shell.
5. **No AI-generated content surfaces without a "human-editable" fallback.**
   Auto alt-text, simplifications, and transcripts are always editable and
   flagged `AI-generated` in the DOM.
6. **No cognitive-load auth.** Every flow must offer at least one
   non-password option (magic link, SSO, WebAuthn).
7. **Indic-language support is not optional.** At minimum Hindi + English
   must be available on every user-facing surface by Phase 2.

---

## 6. Verification process

Per PR:

1. Automated checks run in CI (`pnpm lint`, `pnpm test`, `pnpm a11y`).
2. Reviewer checks the **Accessibility checklist** in the PR template.

Per milestone:

1. Manual pass using the Manual items above.
2. Screen-reader walkthrough (NVDA / VoiceOver / TalkBack at minimum one each).
3. Keyboard-only walkthrough from cold start to task completion.
4. High-contrast theme verified.
5. 200% zoom + text-spacing overrides verified.

Per major release:

1. External accessibility audit against this checklist.
2. AT user testing (at least two users from the disability community per
   user journey).
