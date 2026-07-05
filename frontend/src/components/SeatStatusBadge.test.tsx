import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SeatStatusBadge } from './SeatStatusBadge';
import { SeatStatus } from '@/types/seat';

describe('SeatStatusBadge', () => {
  it.each([
    ['AVAILABLE', 'bg-emerald-500'],
    ['IN_USE', 'bg-orange-500'],
    ['PAUSED', 'bg-yellow-500'],
    ['RESERVED', 'bg-blue-500'],
    ['MAINTENANCE', 'bg-gray-500'],
    ['OFFLINE', 'bg-slate-500'],
    ['BOOTING', 'bg-blue-400'],
    ['UNREACHABLE', 'bg-red-500'],
  ] as [string, string][])('renders %s with correct colour classes', (status, cls) => {
    render(<SeatStatusBadge status={status as SeatStatus} />);
    const badge = screen.getByLabelText(`Seat status: ${status}`);
    expect(badge).toBeInTheDocument();
    // The dot should have the correct bg colour
    const dot = badge.querySelector('span');
    expect(dot).toHaveClass(cls);
  });

  it.each([
    [SeatStatus.AVAILABLE, 'Available'],
    [SeatStatus.IN_USE, 'In Use'],
    [SeatStatus.PAUSED, 'Paused'],
    [SeatStatus.RESERVED, 'Reserved'],
    [SeatStatus.MAINTENANCE, 'Maintenance'],
    [SeatStatus.OFFLINE, 'Offline'],
    [SeatStatus.BOOTING, 'Booting'],
    [SeatStatus.UNREACHABLE, 'Unreachable'],
  ])("renders human-readable label for %s", (status, expectedLabel) => {
    render(<SeatStatusBadge status={status} />);
    expect(screen.getByText(expectedLabel)).toBeInTheDocument();
  });
});
