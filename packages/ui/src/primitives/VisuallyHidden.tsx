import { Root as RadixVisuallyHidden } from '@radix-ui/react-visually-hidden';

import type { ComponentPropsWithoutRef } from 'react';

/**
 * Renders content that is hidden visually but remains available to
 * assistive technology. Use for icon-only buttons, skip-link targets,
 * and "more context for screen readers" patterns.
 *
 * @example
 * <button>
 *   <TrashIcon aria-hidden="true" />
 *   <VisuallyHidden>Delete attachment</VisuallyHidden>
 * </button>
 */
export function VisuallyHidden(
  props: ComponentPropsWithoutRef<typeof RadixVisuallyHidden>,
) {
  return <RadixVisuallyHidden {...props} />;
}
