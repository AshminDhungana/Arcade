import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Modal } from './Modal';

describe('Modal', () => {
  it('renders dialog with title when open, closes on Escape and close button', () => {
    const onClose = vi.fn();
    render(<Modal open onClose={onClose} title="Test Title"><p>body</p></Modal>);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveTextContent('Test Title');
    expect(dialog).toHaveTextContent('body');

    // Escape key closes
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);

    // Close button closes
    const closeBtn = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('does not render dialog when open is false', () => {
    const onClose = vi.fn();
    render(<Modal open={false} onClose={onClose} title="Test Title"><p>body</p></Modal>);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
