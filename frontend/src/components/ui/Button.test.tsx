import { test, vi, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

test('primary button calls onClick and shows spinner when loading', () => {
  const onClick = vi.fn();
  render(<Button variant="primary" loading onClick={onClick}>Save</Button>);
  const btn = screen.getByRole('button', { name: /save/i });
  expect(btn).toBeDisabled();
  fireEvent.click(btn); // still disabled -> onClick not called
  expect(onClick).not.toHaveBeenCalled();
});
