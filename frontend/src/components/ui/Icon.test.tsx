// frontend/src/components/ui/Icon.test.tsx
import { render, screen } from '@testing-library/react';
import { Icon, FaviconIcon } from './Icon';

describe('Icon component', () => {
  it('renders GamepadDirectional with stroke variant at default size', () => {
    render(<Icon name="GamepadDirectional" variant="stroke" />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveAttribute('stroke', 'currentColor');
    expect(svg).toHaveAttribute('fill', 'none');
    expect(svg).toHaveAttribute('stroke-width', '2');
  });

  it('renders fill variant with fill="currentColor" and stroke="none"', () => {
    render(<Icon name="GamepadDirectional" variant="fill" />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveAttribute('fill', 'currentColor');
    expect(svg).toHaveAttribute('stroke', 'none');
  });

  it('applies correct size class for size={56}', () => {
    render(<Icon name="GamepadDirectional" size={56} />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveClass('h-14');
    expect(svg).toHaveClass('w-14');
  });

  it('applies correct size class for size={32}', () => {
    render(<Icon name="GamepadDirectional" size={32} />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveClass('h-8');
    expect(svg).toHaveClass('w-8');
  });

  it('applies correct size class for size={28}', () => {
    render(<Icon name="GamepadDirectional" size={28} />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveClass('h-7');
    expect(svg).toHaveClass('w-7');
  });

  it('applies correct size class for size={14}', () => {
    render(<Icon name="GamepadDirectional" size={14} />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveClass('h-3.5');
    expect(svg).toHaveClass('w-3.5');
  });

  it('defaults to size={24} when size not provided', () => {
    render(<Icon name="GamepadDirectional" />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveClass('h-6');
    expect(svg).toHaveClass('w-6');
  });

  it('passes custom className through', () => {
    render(<Icon name="GamepadDirectional" className="text-primary" />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveClass('text-primary');
  });

  it('sets aria-hidden="true" by default', () => {
    render(<Icon name="GamepadDirectional" />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  it('allows overriding aria-hidden', () => {
    render(<Icon name="GamepadDirectional" aria-hidden={false} />);
    const svg = screen.getByRole('img', { hidden: false });
    expect(svg).toHaveAttribute('aria-hidden', 'false');
  });

  it('throws TypeScript error for invalid name (compile-time)', () => {
    // @ts-expect-error invalid icon name
    <Icon name="NonExistentIcon" />;
    // placeholder — TS catches this
  });

  it('throws TypeScript error for invalid size (compile-time)', () => {
    // @ts-expect-error invalid size
    <Icon name="GamepadDirectional" size={999} />;
    // placeholder — TS catches this
  });

  it('does not apply motion props when motion="none" (default)', () => {
    render(<Icon name="GamepadDirectional" motion="none" />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).not.toHaveAttribute('initial');
    expect(svg).not.toHaveAttribute('animate');
  });

  it('renders without motion wrapper when motion="entrance" but size < 32', () => {
    render(<Icon name="GamepadDirectional" size={24} motion="entrance" />);
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg.tagName.toLowerCase()).toBe('svg');
  });
});

describe('FaviconIcon constant', () => {
  it('is a valid SVG string with viewBox', () => {
    expect(FaviconIcon).toContain('<svg');
    expect(FaviconIcon).toContain('viewBox="0 0 24 24"');
  });

  it('uses stroke variant (no fill)', () => {
    expect(FaviconIcon).toContain('stroke="currentColor"');
    expect(FaviconIcon).toContain('fill="none"');
  });

  it('has stroke-width="2"', () => {
    expect(FaviconIcon).toContain('stroke-width="2"');
  });

  it('is fixed at 32x32', () => {
    expect(FaviconIcon).toContain('width="32"');
    expect(FaviconIcon).toContain('height="32"');
  });

  it('contains GamepadDirectional paths', () => {
    // GamepadDirectional has 4 path elements
    const pathCount = (FaviconIcon.match(/<path/g) || []).length;
    expect(pathCount).toBe(4);
  });
});
