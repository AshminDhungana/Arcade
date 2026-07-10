import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EmptyState } from './EmptyState';

describe('EmptyState', () => {
  it('renders the message', () => {
    render(<EmptyState message="No data available" />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('renders the action when provided', () => {
    const action = <button>Add Item</button>;
    render(<EmptyState message="No data" action={action} />);
    expect(screen.getByRole('button', { name: /add item/i })).toBeInTheDocument();
  });
});
