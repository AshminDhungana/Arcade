import { describe, it, expect } from 'vitest';
import { formatDuration, formatHour, formatWeekday, utilisationColor } from './format';

describe('analytics format helpers', () => {
  it('formatDuration renders h/m', () => {
    expect(formatDuration(0)).toBe('0m');
    expect(formatDuration(45 * 60)).toBe('45m');
    expect(formatDuration(3600 + 23 * 60)).toBe('1h 23m');
    expect(formatDuration(-5)).toBe('0m');
  });

  it('formatHour renders 12h AM/PM', () => {
    expect(formatHour(0)).toBe('12 AM');
    expect(formatHour(15)).toBe('3 PM');
    expect(formatHour(12)).toBe('12 PM');
  });

  it('formatWeekday renders short weekday for YYYY-MM-DD', () => {
    expect(formatWeekday('2026-07-13')).toBe('Mon'); // Monday
    expect(formatWeekday('2026-07-15')).toBe('Wed'); // Wednesday
  });

  it('utilisationColor thresholds', () => {
    expect(utilisationColor(10)).toBe('#22C55E');
    expect(utilisationColor(70)).toBe('#F59E0B');
    expect(utilisationColor(90)).toBe('#EF4444');
  });
});
