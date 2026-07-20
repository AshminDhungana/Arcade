import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import Signature from './Signature';

describe('Signature', () => {
  it('renders as a decorative svg using currentColor', () => {
    const { container } = render(<Signature className="h-8 text-foreground" />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute('fill')).toBe('currentColor');
    expect(svg?.getAttribute('aria-hidden')).toBe('true');
    // className must be forwarded to the svg element
    expect(svg?.classList.contains('h-8')).toBe(true);
    expect(svg?.classList.contains('text-foreground')).toBe(true);
    // three signature strokes, copied verbatim from public/sign.svg
    expect(svg?.querySelectorAll('path').length).toBe(3);
  });
});
