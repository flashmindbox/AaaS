import { Slot } from '@radix-ui/react-slot';
import { clsx } from 'clsx';
import { forwardRef } from 'react';

import type { ButtonHTMLAttributes } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Render as the child element (for `<a>` pretending to be a button via role). */
  asChild?: boolean;
  /**
   * When true, the button announces its loading state to assistive tech and
   * disables pointer activation (but remains focusable for screen reader context).
   */
  loading?: boolean;
}

/**
 * Accessible button primitive.
 *
 * - Minimum target size 44x44 CSS px (WCAG 2.5.8)
 * - Visible focus ring (WCAG 2.4.7)
 * - `aria-busy` and `aria-disabled` wired from the `loading` prop
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    asChild = false,
    loading = false,
    className,
    type,
    children,
    disabled,
    ...rest
  },
  ref,
) {
  const Comp = asChild ? Slot : 'button';
  return (
    <Comp
      ref={ref}
      type={asChild ? undefined : type ?? 'button'}
      className={clsx('aaas-btn', `aaas-btn--${variant}`, `aaas-btn--${size}`, className)}
      aria-busy={loading || undefined}
      aria-disabled={disabled || loading || undefined}
      disabled={disabled || loading}
      {...rest}
    >
      {children}
    </Comp>
  );
});
