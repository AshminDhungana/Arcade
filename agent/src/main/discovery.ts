/**
 * LAN discovery client for the Arcade Agent.
 *
 * Listens for the server's UDP beacon and resolves it to a `ws://host:port`
 * URL. The HTTP `/api/discovery` fallback is intentionally deferred to the
 * settings UI task; when UDP yields nothing we return null.
 */

import dgram from 'node:dgram';

const BEACON_PORT = 48123;
const BEACON_MAGIC = 'ARCADE_DISCOVERY';

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

/**
 * Discover the Arcade server on the LAN.
 *
 * Primary path is a UDP listen on the beacon port. On any timeout or error
 * the UDP attempt resolves to null and we fall through to the (currently
 * unimplemented) HTTP fallback, which also returns null.
 *
 * @param timeoutMs How long to wait for a beacon before giving up.
 * @returns A `ws://host:port` URL, or null if no server was discovered.
 */
export async function discoverServer(timeoutMs = 4000): Promise<string | null> {
  // 1) Try UDP broadcast beacon.
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
  if (udp) return udp;

  // 2) Fallback: probe common LAN gateways via HTTP /api/discovery.
  //    Operators on strict networks can also hard-set server_url in config.
  return null; // UDP is the primary path; HTTP fallback added with settings UI.
}
