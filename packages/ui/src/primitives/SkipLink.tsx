import type { ComponentPropsWithoutRef } from 'react';

/**
 * A keyboard-only navigation shortcut that appears on focus.
 * Required by WCAG 2.4.1 "Bypass Blocks".
 *
 * Render this as the very first focusable element on the page:
 *
 *   <SkipLink href="#main">Skip to main content</SkipLink>
 *   ...
 *   <main id="main" tabIndex={-1}>...</main>
 */
export function SkipLink({
  href = '#main',
  children = 'Skip to main content',
  ...rest
}: ComponentPropsWithoutRef<'a'>) {
  return (
    <a
      href={href}
      {...rest}
      style={{
        position: 'absolute',
        left: '-9999px',
        top: 0,
        zIndex: 9999,
        padding: '12px 16px',
        background: '#0B2447',
        color: '#FFFFFF',
        fontWeight: 600,
        textDecoration: 'none',
        ...rest.style,
      }}
      onFocus={(e) => {
        e.currentTarget.style.left = '8px';
        e.currentTarget.style.top = '8px';
        rest.onFocus?.(e);
      }}
      onBlur={(e) => {
        e.currentTarget.style.left = '-9999px';
        rest.onBlur?.(e);
      }}
    >
      {children}
    </a>
  );
}
