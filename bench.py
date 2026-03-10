#!/usr/bin/env python3
"""bench - HTTP endpoint benchmarker.

One file. Zero deps. Load test anything.

Usage:
  bench.py https://example.com               → 100 requests, 10 concurrent
  bench.py https://example.com -n 500 -c 20  → 500 reqs, 20 concurrent
  bench.py https://api.com/data -m POST -d '{"key":"val"}'
  bench.py https://example.com --json         → JSON output
"""

import argparse
import json
import statistics
import sys
import threading
import time
import urllib.request
import urllib.error


def do_request(url: str, method: str = "GET", data: str = None,
               headers: dict = None, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    body = data.encode() if data else None
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, body, timeout=timeout) as r:
            r.read()
            elapsed = time.monotonic() - start
            return {"status": r.status, "time": elapsed, "error": None}
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        return {"status": e.code, "time": elapsed, "error": None}
    except Exception as e:
        elapsed = time.monotonic() - start
        return {"status": 0, "time": elapsed, "error": str(e)}


def run_bench(url: str, n: int, c: int, method: str = "GET",
              data: str = None, headers: dict = None, timeout: int = 10):
    results = []
    lock = threading.Lock()
    counter = [0]

    def worker():
        while True:
            with lock:
                idx = counter[0]
                if idx >= n:
                    return
                counter[0] += 1
            r = do_request(url, method, data, headers, timeout)
            with lock:
                results.append(r)

    start = time.monotonic()
    threads = []
    for _ in range(min(c, n)):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    total_time = time.monotonic() - start

    return results, total_time


def print_results(results: list[dict], total_time: float, url: str, as_json: bool = False):
    times = [r["time"] for r in results if not r["error"]]
    errors = [r for r in results if r["error"]]
    statuses = {}
    for r in results:
        s = r["status"]
        statuses[s] = statuses.get(s, 0) + 1

    data = {
        "url": url,
        "requests": len(results),
        "errors": len(errors),
        "total_time_s": round(total_time, 3),
        "rps": round(len(results) / total_time, 1) if total_time > 0 else 0,
        "statuses": statuses,
    }

    if times:
        data.update({
            "min_ms": round(min(times) * 1000, 1),
            "max_ms": round(max(times) * 1000, 1),
            "mean_ms": round(statistics.mean(times) * 1000, 1),
            "median_ms": round(statistics.median(times) * 1000, 1),
            "p95_ms": round(sorted(times)[int(len(times) * 0.95)] * 1000, 1),
            "p99_ms": round(sorted(times)[int(len(times) * 0.99)] * 1000, 1),
            "stdev_ms": round(statistics.stdev(times) * 1000, 1) if len(times) > 1 else 0,
        })

    if as_json:
        print(json.dumps(data, indent=2))
        return

    print(f"\n  URL:        {url}")
    print(f"  Requests:   {data['requests']} ({data['errors']} errors)")
    print(f"  Total:      {data['total_time_s']}s")
    print(f"  RPS:        {data['rps']}")
    if times:
        print(f"  Latency:")
        print(f"    Min:      {data['min_ms']}ms")
        print(f"    Mean:     {data['mean_ms']}ms")
        print(f"    Median:   {data['median_ms']}ms")
        print(f"    P95:      {data['p95_ms']}ms")
        print(f"    P99:      {data['p99_ms']}ms")
        print(f"    Max:      {data['max_ms']}ms")
    if statuses:
        print(f"  Status codes:")
        for s, count in sorted(statuses.items()):
            print(f"    {s}: {count}")


def main():
    p = argparse.ArgumentParser(description="HTTP endpoint benchmarker")
    p.add_argument("url")
    p.add_argument("-n", "--requests", type=int, default=100)
    p.add_argument("-c", "--concurrency", type=int, default=10)
    p.add_argument("-m", "--method", default="GET")
    p.add_argument("-d", "--data")
    p.add_argument("-H", "--header", action="append", default=[])
    p.add_argument("-t", "--timeout", type=int, default=10)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    headers = {}
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    if not args.json:
        print(f"Benchmarking {args.url} ({args.requests} requests, {args.concurrency} concurrent)...")

    results, total = run_bench(args.url, args.requests, args.concurrency,
                                args.method, args.data, headers, args.timeout)
    print_results(results, total, args.url, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
