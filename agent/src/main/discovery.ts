/**
 * LAN discovery client for the Arcade Agent.
 *
 * 1) Listens for the server's UDP beacon (port 48123) for up to timeoutMs.
 * 2) Falls back to probing common LAN gateways via HTTP GET /api/discovery.
 * 3) Falls back to localhost (for same-machine testing).
 */

import dgram from 'node:dgram';

const BEACON_PORT = 48123;
const BEACON_MAGIC = 'ARCADE_DISCOVERY';

/** Common LAN gateway IPs to probe for HTTP /api/discovery fallback. */
const COMMON_GATEWAYS = [
  '192.168.1.1', '192.168.0.1', '192.168.1.254', '192.168.0.254',
  '10.0.0.1', '10.0.1.1', '10.1.1.1',
  '172.16.0.1', '172.16.1.1',
];

/** Localhost fallbacks for same-machine testing when server returns 0.0.0.0. */
const LOCALHOST_FALLBACKS = ['127.0.0.1', 'localhost'];

const PROBE_TIMEOUT_MS = 500;
const MAX_CONCURRENT_PROBES = 3;

/** Extract host:port from a ws:// URL. */
function parseWsUrl(wsUrl: string): { host: string; port: number } | null {
  try {
    const url = new URL(wsUrl);
    return { host: url.hostname, port: url.port ? parseInt(url.port, 10) : 80 };
  } catch {
    return null;
  }
}

/** Probe a single IP:port via HTTP /api/discovery. */
async function probeHostPort(host: string, port: number): Promise<string | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const res = await fetch(`http://${host}:${port}/api/discovery`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    clearTimeout(timeout);
    if (!res.ok) return null;
    const data = await res.json() as { host: string; port: number };
    return `ws://${data.host}:${data.port}`;
  } catch {
    clearTimeout(timeout);
    return null;
  }
}

/**
 * Parse a server beacon message into a `ws://host:port` URL.
 *
 * The beacon is `ARCADE_DISCOVERY|<json>` where the JSON payload is
 * `{"host":..., "port":..., "cafe_name":...}`. Returns null if the magic
 * prefix is absent or the payload cannot be parsed.
 *
 * @param text The raw beacon text.
 * @returns A `ws://host:port` URL, or null if the beacon is invalid.
 */
function beaconToWsUrl(text: string): string | null {
  const idx = text.indexOf(BEACON_MAGIC);
  if (idx < 0) return null;
  const json = text.slice(idx + BEACON_MAGIC.length + 1);
  try {
    const payload = JSON.parse(json) as { host: string; port: number };
    return `ws://${payload.host}:${payload.port}`;
  } catch {
    return null;
  }
}

/** Probe a single gateway IP via HTTP /api/discovery on port 80. */
async function probeGateway(ip: string): Promise<string | null> {
  return probeHostPort(ip, 80);
}

/**
 * Probe a candidate server URL via HTTP /api/discovery to verify it's reachable.
 * Returns the verified ws:// URL or null if unreachable.
 */
async function verifyServerUrl(wsUrl: string): Promise<string | null> {
  const parsed = parseWsUrl(wsUrl);
  if (!parsed) return null;
  return probeHostPort(parsed.host, parsed.port);
}

/**
 * Discover the Arcade server on the LAN.
 *
 * 1) Try UDP broadcast beacon (timeoutMs, default 4s), then verify via HTTP.
 *    If beacon gives a LAN IP but it's not reachable, try localhost:port immediately.
 * 2) Fallback: probe common LAN gateways AND localhost in parallel via HTTP GET /api/discovery
 *    (parallel, max 3 concurrent, 500ms timeout each).
 *
 * @param timeoutMs How long to wait for a beacon before fallback.
 * @returns A `ws://host:port` URL, or null if no server was discovered.
 */
export async function discoverServer(timeoutMs = 4000): Promise<string | null> {
  // 1) Try UDP broadcast beacon, then verify the returned URL works.
  const udp = await new Promise<string | null>((resolve) => {
    const sock = dgram.createSocket('udp4');
    let done = false;
    const finish = (url: string | null) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      sock.close();
      resolve(url);
    };
    const timer = setTimeout(() => finish(null), timeoutMs);
    sock.on('message', (msg: Buffer) => finish(beaconToWsUrl(msg.toString())));
    sock.on('error', () => finish(null));
    sock.bind(BEACON_PORT);
  });
  let beaconPort: number | null = null;
  if (udp) {
    const verified = await verifyServerUrl(udp);
    if (verified) return verified;
    // UDP beacon gave a URL but it's not reachable (e.g. LAN IP blocked by firewall).
    // Extract the port and try localhost with that port immediately (same-machine scenario).
    const parsed = parseWsUrl(udp);
    if (parsed) {
      beaconPort = parsed.port;
      const localhostResult = await probeHostPort('127.0.0.1', beaconPort);
      if (localhostResult) return localhostResult;
    }
    // Fall through to other discovery methods.
  }

  // 2) Fallback: probe common LAN gateways AND localhost in parallel.
  // Build all candidates: gateways on port 80 + localhost on beacon port (if known) + localhost on default port
  const candidates: Array<{ host: string; port: number }> = [];

  // Add gateway IPs (probe on port 80)
  for (const ip of COMMON_GATEWAYS) {
    candidates.push({ host: ip, port: 80 });
  }

  // Add localhost with beacon port (if we got one from UDP beacon)
  if (beaconPort) {
    candidates.push({ host: '127.0.0.1', port: beaconPort });
  }

  // Add localhost with default server port (8742) and common alternatives
  candidates.push({ host: '127.0.0.1', port: 8742 });
  candidates.push({ host: 'localhost', port: 8742 });

  // Probe in batches of MAX_CONCURRENT_PROBES
  for (let i = 0; i < candidates.length; i += MAX_CONCURRENT_PROBES) {
    const batch = candidates.slice(i, i + MAX_CONCURRENT_PROBES);
    const results = await Promise.all(batch.map(c => probeHostPort(c.host, c.port)));
    const success = results.find((r) => r !== null);
    if (success) return success;
  }

  return null;
}
