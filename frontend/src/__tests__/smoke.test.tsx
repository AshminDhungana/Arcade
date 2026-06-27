import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('smoke', () => {
  it('vitest runs', () => {
    expect(1 + 1).toBe(2);
  });

  it('App renders scaffold heading', () => {
    render(<App />);
    expect(screen.getByText(/Arcade \(scaffold\)/)).toBeInTheDocument();
  });
});
