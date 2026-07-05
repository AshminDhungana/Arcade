import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ElapsedTimer } from './ElapsedTimer';

describe('ElapsedTimer', () => {
  it('renders initial elapsed time for a started session', () => {
    const startedAt = new Date(Date.now() - 1000 * 60 * 5).toISOString(); // 5 min ago
    render(<ElapsedTimer startedAt={startedAt} isRunning />);
    expect(screen.getByLabelText('Elapsed time')).toBeInTheDocument();
  });

  it('shows 00:00:00 when isRunning is false', () => {
    render(<ElapsedTimer startedAt="2024-01-01T00:00:00Z" isRunning={false} />);
    expect(screen.getByLabelText('Elapsed time')).toHaveTextContent('00:00:00');
  });
});
