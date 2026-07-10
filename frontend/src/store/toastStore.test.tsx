import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act } from 'react';
import { render, screen } from '@testing-library/react';
import { toast, useToastStore } from '@/store/toastStore';
import { ToastViewport } from '@/components/ui/Toast';

describe('Toast system', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    act(() => {
      useToastStore.setState({ toasts: [] });
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders toast.success message and auto-dismisses after 4 seconds', () => {
    render(<ToastViewport />);

    act(() => {
      toast.success('Saved');
    });

    expect(screen.getByText('Saved')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4000);
    });

    expect(screen.queryByText('Saved')).not.toBeInTheDocument();
  });

  it('renders toast.error message and auto-dismisses after 4 seconds', () => {
    render(<ToastViewport />);

    act(() => {
      toast.error('Error occurred');
    });

    expect(screen.getByText('Error occurred')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4000);
    });

    expect(screen.queryByText('Error occurred')).not.toBeInTheDocument();
  });

  it('renders multiple toasts and dismisses each independently', () => {
    render(<ToastViewport />);

    act(() => {
      toast.success('First');
      toast.error('Second');
    });

    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.getByText('Second')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4000);
    });

    expect(screen.queryByText('First')).not.toBeInTheDocument();
    expect(screen.queryByText('Second')).not.toBeInTheDocument();
  });

  it('removes toast on click', () => {
    render(<ToastViewport />);

    act(() => {
      toast.success('Click to dismiss');
    });

    expect(screen.getByText('Click to dismiss')).toBeInTheDocument();

    act(() => {
      screen.getByText('Click to dismiss').click();
    });

    expect(screen.queryByText('Click to dismiss')).not.toBeInTheDocument();
  });

  it('renders success toast with green styling and check icon', () => {
    render(<ToastViewport />);

    act(() => {
      toast.success('Success message');
    });

    const toastElement = screen.getByText('Success message').closest('div');
    expect(toastElement).toHaveClass('border-emerald-500/20');
    expect(toastElement).toHaveClass('bg-emerald-900/90');
    expect(toastElement).toHaveClass('text-emerald-200');
    expect(toastElement!.querySelector('.lucide-circle-check-big')).toBeInTheDocument();
  });

  it('renders error toast with red styling and alert icon', () => {
    render(<ToastViewport />);

    act(() => {
      toast.error('Error message');
    });

    const toastElement = screen.getByText('Error message').closest('div');
    expect(toastElement).toHaveClass('border-red-800/50');
    expect(toastElement).toHaveClass('bg-red-900/90');
    expect(toastElement).toHaveClass('text-red-200');
    expect(toastElement!.querySelector('.lucide-circle-alert')).toBeInTheDocument();
  });

  it('toast viewport has aria-live polite for accessibility', () => {
    render(<ToastViewport />);

    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });
});
