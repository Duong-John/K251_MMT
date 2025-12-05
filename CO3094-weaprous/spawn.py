import asyncio
import aiohttp
import time
import argparse

DEFAULT_URL = "http://10.230.199.13:3000"
DEFAULT_REQUESTS = 50 # seconds
DEFAULT_CONCURRENCY = 10 # seconds
REQUEST_TIMEOUT = 8  # seconds

async def fetch(session, idx, url):
    start = time.monotonic()
    try:
        async with session.get(url, timeout=REQUEST_TIMEOUT) as resp:
            body = await resp.text()
            latency = time.monotonic() - start
            
            backend = resp.headers.get("X-Backend") or resp.headers.get("x-backend")
            if not backend:
                
                first_line = ""
                for line in body.splitlines():
                    s = line.strip()
                    if s:
                        first_line = s
                        break
                backend = first_line[:120] if first_line else "<no backend info>"
            return {
                "index": idx,
                "status": resp.status,
                "latency": latency,
                "backend": backend
            }
    except Exception as e:
        latency = time.monotonic() - start
        return {
            "index": idx,
            "status": None,
            "latency": latency,
            "backend": f"ERROR: {e}"
        }

async def worker(name, queue, session, url, results):
    while True:
        try:
            idx = queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        res = await fetch(session, idx, url)
        results.append(res)
        # print per-request summary
        status = res["status"] if res["status"] is not None else "ERR"
        print(f"[{idx:03d}] status={status}  latency={res['latency']:.3f}s  backend={res['backend']}")

async def run(url, total_requests, concurrency):
    q = asyncio.Queue()
    for i in range(1, total_requests + 1):
        q.put_nowait(i)

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    connector = aiohttp.TCPConnector(limit=0)  # let concurrency control handle parallelism
    results = []
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        workers = [
            asyncio.create_task(worker(f"w{i}", q, session, url, results))
            for i in range(concurrency)
        ]
        await asyncio.gather(*workers)

    # summary
    total = len(results)
    successes = sum(1 for r in results if isinstance(r["status"], int) and 200 <= r["status"] < 400)
    failures = total - successes
    latencies = [r["latency"] for r in results if r["status"] is not None]
    avg_latency = sum(latencies)/len(latencies) if latencies else 0
    print("\n=== SUMMARY ===")
    print(f"Target: {url}")
    print(f"Requests: {total}  Concurrency: {concurrency}")
    print(f"Success: {successes}  Failures: {failures}")
    print(f"Average latency (for responded requests): {avg_latency:.3f} s")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=DEFAULT_URL, help="Target URL (default http://10.230.199.13:3000)")
    p.add_argument("--requests", "-n", type=int, default=DEFAULT_REQUESTS, help="Total requests to send")
    p.add_argument("--concurrency", "-c", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent workers")
    return p.parse_args()

def main():
    args = parse_args()
    print(f"Simple proxy test -> {args.url}  requests={args.requests}  concurrency={args.concurrency}")
    try:
        asyncio.run(run(args.url, args.requests, args.concurrency))
    except KeyboardInterrupt:
        print("\nAborted by user")

if __name__ == "__main__":
    main()