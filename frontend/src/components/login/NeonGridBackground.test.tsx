// frontend/src/components/login/NeonGridBackground.test.tsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import NeonGridBackground from './NeonGridBackground';

describe('NeonGridBackground', () => {
  it('renders four stacked, non-interactive layers', () => {
    const { getByTestId } = render(<NeonGridBackground />);
    const root = getByTestId('login-background');
    expect(root.className).toContain('neon-grid');
    expect(root.className).toContain('pointer-events-none');
    expect(root.querySelectorAll(':scope > div').length).toBe(4);
  });
});
