"""
ARCH-01 Stress Test
Runs 10 concurrent increments requests against the running FastAPI server.
Reports whether any `database is locked` (or similar) errors occurred.
"""
import asyncio
import sys
TIMEOUT = 60  # seconds


async def run_concurrent_writes(client_count: int = 10, requests_per_client: int = 20) -> None:
    import httpx

    errors: list[str] = []
    url = "http://127.0.0.1:8001/increment"
    lock = asyncio.Lock()

    async def worker(worker_id: int):
        async with httpx.AsyncClient() as client:
            for i in range(requests_per_client):
                try:
                    resp = await client.post(url, timeout=TIMEOUT)
                    if resp.status_code != 200:
                        await lock.acquire()
                        try:
                            errors.append(f"[worker {worker_id} req {i}] HTTP {resp.status_code}: {resp.text[:200]}")
                        finally:
                            lock.release()
                except Exception as exc:
                    await lock.acquire()
                    try:
                        errors.append(f"[worker {worker_id} req {i}] {type(exc).__name__}: {str(exc)[:200]}")
                    finally:
                        lock.release()

    await asyncio.gather(*[worker(i) for i in range(client_count)])

    if errors:
        print(f"FAIL: {len(errors)} errors occurred during {client_count * requests_per_client} requests:")
        for e in errors[:10]:
            print("   -", e)
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more")
        sys.exit(1)
    else:
        total = client_count * requests_per_client
        print(f"PASS: All {total} concurrent write requests completed without database locking errors.")


if __name__ == "__main__":
    asyncio.run(run_concurrent_writes())
