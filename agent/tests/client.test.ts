import { describe, it, expect, vi } from 'vitest';
import { AgentWebSocketClient } from '../src/main/ws/client.js';
import type { IPlatformService } from '../src/main/platform/types.js';

function makeFakePlatform(): IPlatformService {
  return {
    showKioskOverlay: vi.fn(),
    hideKioskOverlay: vi.fn(),
    updateTimer: vi.fn(),
    sendAnnouncement: vi.fn(),
    isKioskVisible: () => false,
    restartPC: vi.fn(),
    shutdownPC: vi.fn(),
    captureScreenshot: vi.fn(),
    enableAutoStart: vi.fn(),
    disableAutoStart: vi.fn(),
    getSystemInfo: vi.fn(),
  } as unknown as IPlatformService;
}

const baseConfig = {
  server_url: 'ws://localhost:8000',
  seat_id: 'seat_001',
  agent_secret: 'secret',
};

describe('AgentWebSocketClient REGISTERED', () => {
  it('captures cafe_name from the REGISTERED reply', async () => {
    const client = new AgentWebSocketClient(baseConfig as any, makeFakePlatform(), undefined);
    await client.handleMessage({
      data: JSON.stringify({
        type: 'REGISTERED',
        payload: { seat_id: 'seat_001', cafe_name: 'Neon Cafe' },
      }),
    } as any);
    expect(client.getCafeName()).toBe('Neon Cafe');
  });

  it('captures event_banner from the REGISTERED reply', async () => {
    const client = new AgentWebSocketClient(baseConfig as any, makeFakePlatform(), undefined);
    await client.handleMessage({
      data: JSON.stringify({
        type: 'REGISTERED',
        payload: { seat_id: 'seat_001', cafe_name: 'Neon Cafe', event_banner: 'Summer Tournament!' },
      }),
    } as any);
    expect(client.getCafeName()).toBe('Neon Cafe');
    expect((client as any).eventBanner).toBe('Summer Tournament!');
  });
});
