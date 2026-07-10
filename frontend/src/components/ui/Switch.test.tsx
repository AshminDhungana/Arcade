import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Switch } from './Switch';

describe('Switch', () => {
  it('renders switch with role="switch" and reflects checked state', () => {
    render(<Switch checked={false} onCheckedChange={vi.fn()} label="Test" />);
    const sw = screen.getByRole('switch');
    expect(sw).toBeInTheDocument();
    expect(sw).not.toBeChecked();
    expect(sw).toHaveAttribute('aria-checked', 'false');
  });

  it('toggles onCheckedChange when clicked', () => {
    const onCheckedChange = vi.fn();
    render(<Switch checked={false} onCheckedChange={onCheckedChange} label="Test" />);
    const sw = screen.getByRole('switch');
    fireEvent.click(sw);
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it('toggles onCheckedChange when Enter is pressed', () => {
    const onCheckedChange = vi.fn();
    render(<Switch checked={false} onCheckedChange={onCheckedChange} label="Test" />);
    const sw = screen.getByRole('switch');
    fireEvent.keyDown(sw, { key: 'Enter', code: 'Enter' });
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it('toggles onCheckedChange when Space is pressed', () => {
    const onCheckedChange = vi.fn();
    render(<Switch checked={false} onCheckedChange={onCheckedChange} label="Test" />);
    const sw = screen.getByRole('switch');
    fireEvent.keyDown(sw, { key: ' ', code: 'Space' });
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it('does not call onCheckedChange when disabled', () => {
    const onCheckedChange = vi.fn();
    render(<Switch checked={false} onCheckedChange={onCheckedChange} label="Test" disabled />);
    const sw = screen.getByRole('switch');
    expect(sw).toBeDisabled();
    fireEvent.click(sw);
    expect(onCheckedChange).not.toHaveBeenCalled();
  });

  it('renders label and description', () => {
    render(<Switch checked={false} onCheckedChange={vi.fn()} label="Feature Flag" description="Enable or disable feature" />);
    expect(screen.getByText('Feature Flag')).toBeInTheDocument();
    expect(screen.getByText('Enable or disable feature')).toBeInTheDocument();
  });
});
