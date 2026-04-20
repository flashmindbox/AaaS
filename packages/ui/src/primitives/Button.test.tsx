import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { Button } from './Button';

describe('<Button />', () => {
  it('renders children and has accessible name', () => {
    render(<Button>Save profile</Button>);
    expect(screen.getByRole('button', { name: 'Save profile' })).toBeInTheDocument();
  });

  it('defaults type="button" to avoid accidental form submits', () => {
    render(<Button>Click</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('exposes aria-busy when loading', () => {
    render(<Button loading>Saving</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });

  it('passes axe-core accessibility audit', async () => {
    const { container } = render(<Button>Accessible</Button>);
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
