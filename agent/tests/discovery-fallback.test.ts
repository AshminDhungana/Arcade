/**
 * Tests for HTTP /api/discovery fallback in agent discovery client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock dgram with importOriginal to properly mock createSocket
vi.mock('node:dgram', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    createSocket: vi.fn(),
  };
});

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

import { discoverServer } from '../src/main/discovery.js';
import * as dgram from 'node:dgram';

describe('discoverServer HTTP fallback', () => {
  let mockSocket: {
    on: ReturnType<typeof vi.fn>;
    bind: ReturnType<typeof vi.fn>;
    close: ReturnType<typeof vi.fn>;
    _messageHandler: ((msg: Buffer) => void) | null;
    _errorHandler: ((err: Error) => void) | null;
  };

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.useFakeTimers();

    mockSocket = {
      on: vi.fn(),
      bind: vi.fn(),
      close: vi.fn(),
      _messageHandler: null,
      _errorHandler: null,
    };

    (dgram.createSocket as ReturnType<typeof vi.fn>).mockReturnValue(mockSocket);
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns ws URL from HTTP /api/discovery when UDP times out', async () => {
    mockFetch
      .mockRejectedValueOnce(new Error('network error'))  // 192.168.1.1 fails
      .mockRejectedValueOnce(new Error('network error'))  // 192.168.0.1 fails
      .mockResolvedValueOnce({  // 192.168.1.254 succeeds
        ok: true,
        json: async () => ({ host: '192.168.0.100', port: 8741 }),
      });

    const promise = discoverServer(4000);
    await vi.advanceTimersByTimeAsync(4100);  // Past UDP timeout
    const result = await promise;

    expect(result).toBe('ws://192.168.0.100:8741');
    expect(mockFetch).toHaveBeenCalledTimes(3);  // First batch of 3
    expect(mockFetch).toHaveBeenCalledWith('http://192.168.1.1:80/api/discovery', expect.any(Object));
    expect(mockFetch).toHaveBeenCalledWith('http://192.168.0.1:80/api/discovery', expect.any(Object));
    expect(mockFetch).toHaveBeenCalledWith('http://192.168.1.254:80/api/discovery', expect.any(Object));
  });

  it('returns null when all HTTP probes fail', async () => {
    mockFetch.mockRejectedValue(new Error('network error'));

    const promise = discoverServer(4000);
    await vi.advanceTimersByTimeAsync(4100);
    const result = await promise;

    expect(result).toBeNull();
  });

  it('probes max 3 gateways concurrently', async () => {
    let concurrent = 0;
    let maxConcurrent = 0;

    mockFetch.mockImplementation(() => {
      concurrent++;
      maxConcurrent = Math.max(maxConcurrent, concurrent);
      return new Promise(resolve => setTimeout(() => {
        concurrent--;
        resolve({ ok: false, status: 500 });
      }, 50));
    });

    const promise = discoverServer(4000);
    await vi.advanceTimersByTimeAsync(4100);
    await vi.runAllTimersAsync();  // Run all pending timers
    await promise;

    expect(maxConcurrent).toBeLessThanOrEqual(3);
  });
});
