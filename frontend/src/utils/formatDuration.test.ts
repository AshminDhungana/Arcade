// frontend/src/utils/formatDuration.test.ts
import { describe, it, expect } from 'vitest';
import { formatDuration } from './formatDuration';

describe('formatDuration', () => {
  it('formats seconds < 60', () => {
    expect(formatDuration(30)).toBe('30s');
    expect(formatDuration(59)).toBe('59s');
  });

  it('formats minutes < 60', () => {
    expect(formatDuration(60)).toBe('1m');
    expect(formatDuration(90)).toBe('1m 30s');
    expect(formatDuration(2999)).toBe('49m 59s');
  });

  it('formats hours', () => {
    expect(formatDuration(3600)).toBe('1h');
    expect(formatDuration(5400)).toBe('1h 30m');
    expect(formatDuration(90061)).toBe('25h 1m 1s');
  });

  it('handles zero', () => {
    expect(formatDuration(0)).toBe('0s');
  });
});
