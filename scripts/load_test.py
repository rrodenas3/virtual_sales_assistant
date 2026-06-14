import asyncio
import statistics
import time

import httpx

TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


async def one(client: httpx.AsyncClient) -> float:
    started = time.perf_counter()
    await client.post(
        "/api/v1/agent/osa-summary",
        json={"territory_code": "WEST-01", "store_id": "ST-001", "session_id": "load-test", "alert_ids": []},
    )
    return (time.perf_counter() - started) * 1000


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:8000", headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        latencies = await asyncio.gather(*(one(client) for _ in range(50)))
    p95 = statistics.quantiles(latencies, n=20)[18]
    print(f"p95={p95:.0f}ms avg={statistics.mean(latencies):.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())

