/**
 * WCAG 2.2 Level A + AA success criteria, machine-readable.
 *
 * Each entry maps a criterion to (a) the axe-core rule(s) that detect it,
 * and (b) a note about what must still be reviewed manually. Axe cannot
 * catch everything — the `manualCheck` field makes that explicit.
 */

export type WcagLevel = 'A' | 'AA' | 'AAA';

export interface WcagCriterion {
  id: string; // e.g. "1.4.3"
  title: string;
  level: WcagLevel;
  axeRules: string[]; // empty = no axe coverage, manual only
  manualCheck?: string;
}

export const WCAG_22_CHECKLIST: WcagCriterion[] = [
  // 1. Perceivable
  {
    id: '1.1.1',
    title: 'Non-text Content',
    level: 'A',
    axeRules: ['image-alt', 'input-image-alt', 'area-alt', 'svg-img-alt'],
  },
  {
    id: '1.2.1',
    title: 'Audio-only and Video-only (Prerecorded)',
    level: 'A',
    axeRules: [],
    manualCheck: 'Verify transcripts for audio-only and descriptions for video-only.',
  },
  {
    id: '1.2.2',
    title: 'Captions (Prerecorded)',
    level: 'A',
    axeRules: ['video-caption'],
  },
  {
    id: '1.2.3',
    title: 'Audio Description or Media Alternative',
    level: 'A',
    axeRules: [],
    manualCheck: 'Verify AD track or text alternative for each video.',
  },
  {
    id: '1.2.4',
    title: 'Captions (Live)',
    level: 'AA',
    axeRules: [],
    manualCheck: 'Verify live captions on streamed video.',
  },
  {
    id: '1.2.5',
    title: 'Audio Description (Prerecorded)',
    level: 'AA',
    axeRules: [],
    manualCheck: 'Verify AD track.',
  },
  { id: '1.3.1', title: 'Info and Relationships', level: 'A', axeRules: ['list', 'listitem', 'definition-list', 'dlitem', 'label', 'th-has-data-cells', 'td-headers-attr'] },
  { id: '1.3.2', title: 'Meaningful Sequence', level: 'A', axeRules: [] , manualCheck: 'Verify reading order with screen reader.'},
  { id: '1.3.3', title: 'Sensory Characteristics', level: 'A', axeRules: [], manualCheck: 'Do not rely on shape/location alone.' },
  { id: '1.3.4', title: 'Orientation', level: 'AA', axeRules: ['css-orientation-lock'] },
  { id: '1.3.5', title: 'Identify Input Purpose', level: 'AA', axeRules: ['autocomplete-valid'] },
  { id: '1.4.1', title: 'Use of Color', level: 'A', axeRules: ['link-in-text-block'], manualCheck: 'Color alone must not convey meaning.' },
  { id: '1.4.2', title: 'Audio Control', level: 'A', axeRules: ['no-autoplay-audio'] },
  { id: '1.4.3', title: 'Contrast (Minimum)', level: 'AA', axeRules: ['color-contrast'] },
  { id: '1.4.4', title: 'Resize Text', level: 'AA', axeRules: ['meta-viewport'] },
  { id: '1.4.5', title: 'Images of Text', level: 'AA', axeRules: [], manualCheck: 'Use real text not image-of-text.' },
  { id: '1.4.10', title: 'Reflow', level: 'AA', axeRules: [], manualCheck: 'Content reflows at 320 CSS px wide.' },
  { id: '1.4.11', title: 'Non-text Contrast', level: 'AA', axeRules: ['color-contrast-enhanced'] },
  { id: '1.4.12', title: 'Text Spacing', level: 'AA', axeRules: [], manualCheck: 'Apply extended spacing rules and confirm no loss of content.' },
  { id: '1.4.13', title: 'Content on Hover or Focus', level: 'AA', axeRules: [], manualCheck: 'Hoverable/focusable popups must be dismissable, hoverable, persistent.' },

  // 2. Operable
  { id: '2.1.1', title: 'Keyboard', level: 'A', axeRules: ['scrollable-region-focusable'], manualCheck: 'All functionality via keyboard.' },
  { id: '2.1.2', title: 'No Keyboard Trap', level: 'A', axeRules: [], manualCheck: 'Focus can leave every widget via keyboard.' },
  { id: '2.1.4', title: 'Character Key Shortcuts', level: 'A', axeRules: [], manualCheck: 'Single-key shortcuts turn off or are remappable.' },
  { id: '2.2.1', title: 'Timing Adjustable', level: 'A', axeRules: [], manualCheck: 'Time-limited content extendable/dismissable.' },
  { id: '2.2.2', title: 'Pause, Stop, Hide', level: 'A', axeRules: ['meta-refresh'] },
  { id: '2.3.1', title: 'Three Flashes or Below Threshold', level: 'A', axeRules: [], manualCheck: 'No flash > 3 times/sec above threshold.' },
  { id: '2.4.1', title: 'Bypass Blocks', level: 'A', axeRules: ['bypass', 'skip-link'] },
  { id: '2.4.2', title: 'Page Titled', level: 'A', axeRules: ['document-title'] },
  { id: '2.4.3', title: 'Focus Order', level: 'A', axeRules: ['tabindex'] },
  { id: '2.4.4', title: 'Link Purpose (In Context)', level: 'A', axeRules: ['link-name'] },
  { id: '2.4.5', title: 'Multiple Ways', level: 'AA', axeRules: [], manualCheck: 'Nav, search, or sitemap available.' },
  { id: '2.4.6', title: 'Headings and Labels', level: 'AA', axeRules: ['empty-heading', 'heading-order'] },
  { id: '2.4.7', title: 'Focus Visible', level: 'AA', axeRules: ['focus-order-semantics'] },
  { id: '2.4.11', title: 'Focus Not Obscured (Minimum)', level: 'AA', axeRules: [], manualCheck: 'Focused element not fully hidden by author content.' },
  { id: '2.5.1', title: 'Pointer Gestures', level: 'A', axeRules: [], manualCheck: 'Multi-point/path gestures have single-pointer alternative.' },
  { id: '2.5.2', title: 'Pointer Cancellation', level: 'A', axeRules: [], manualCheck: 'Down-event does not trigger; up-event can be aborted.' },
  { id: '2.5.3', title: 'Label in Name', level: 'A', axeRules: ['label-content-name-mismatch'] },
  { id: '2.5.4', title: 'Motion Actuation', level: 'A', axeRules: [], manualCheck: 'Motion-triggered features have UI alternative and can be disabled.' },
  { id: '2.5.7', title: 'Dragging Movements', level: 'AA', axeRules: [], manualCheck: 'Drag-to-rearrange has a single-pointer alternative.' },
  { id: '2.5.8', title: 'Target Size (Minimum)', level: 'AA', axeRules: ['target-size'] },

  // 3. Understandable
  { id: '3.1.1', title: 'Language of Page', level: 'A', axeRules: ['html-has-lang', 'html-lang-valid'] },
  { id: '3.1.2', title: 'Language of Parts', level: 'AA', axeRules: ['valid-lang'] },
  { id: '3.2.1', title: 'On Focus', level: 'A', axeRules: [], manualCheck: 'Focus does not trigger context change.' },
  { id: '3.2.2', title: 'On Input', level: 'A', axeRules: [], manualCheck: 'Input does not trigger unexpected context change.' },
  { id: '3.2.3', title: 'Consistent Navigation', level: 'AA', axeRules: [] },
  { id: '3.2.4', title: 'Consistent Identification', level: 'AA', axeRules: [] },
  { id: '3.2.6', title: 'Consistent Help', level: 'A', axeRules: [], manualCheck: 'Help mechanisms appear in same relative order.' },
  { id: '3.3.1', title: 'Error Identification', level: 'A', axeRules: ['aria-valid-attr-value'] },
  { id: '3.3.2', title: 'Labels or Instructions', level: 'A', axeRules: ['label', 'form-field-multiple-labels'] },
  { id: '3.3.3', title: 'Error Suggestion', level: 'AA', axeRules: [], manualCheck: 'Form errors suggest fixes.' },
  { id: '3.3.4', title: 'Error Prevention (Legal, Financial, Data)', level: 'AA', axeRules: [], manualCheck: 'Reversible, checked, or confirmed.' },
  { id: '3.3.7', title: 'Redundant Entry', level: 'A', axeRules: [], manualCheck: 'Previously-entered info auto-populated or selectable.' },
  { id: '3.3.8', title: 'Accessible Authentication (Minimum)', level: 'AA', axeRules: [], manualCheck: 'No cognitive function test required for auth.' },

  // 4. Robust
  { id: '4.1.2', title: 'Name, Role, Value', level: 'A', axeRules: ['aria-allowed-attr', 'aria-required-attr', 'aria-roles', 'aria-valid-attr', 'button-name'] },
  { id: '4.1.3', title: 'Status Messages', level: 'AA', axeRules: ['aria-live-region-ids'] },
];

/** Flatten the checklist into the list of axe rules we rely on for automated coverage. */
export function axeRulesForWcagAA(): string[] {
  const set = new Set<string>();
  for (const c of WCAG_22_CHECKLIST) {
    if (c.level === 'A' || c.level === 'AA') {
      c.axeRules.forEach((r) => set.add(r));
    }
  }
  return [...set];
}

/** Criteria that require manual verification (no automated coverage). */
export function manualOnlyCriteria(): WcagCriterion[] {
  return WCAG_22_CHECKLIST.filter((c) => c.axeRules.length === 0);
}
