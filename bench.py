#!/usr/bin/env python3
"""bench - Command benchmarking tool.

Time commands, compare alternatives, statistical analysis. Zero dependencies.
"""

import argparse
import math
import os
import subprocess
import sys
import time
import json


def run_cmd(cmd, shell=True):
    start = time.perf_counter()
    r = subprocess.run(cmd, shell=shell, capture_output=True)
    elapsed = time.perf_counter() - start
    return {"time": elapsed, "exit": r.returncode, "stdout_len": len(r.stdout), "stderr_len": len(r.stderr)}


def stats(times):
    n = len(times)
    avg = sum(times) / n
    if n > 1:
        var = sum((t - avg) ** 2 for t in times) / (n - 1)
        sd = math.sqrt(var)
    else:
        sd = 0
    return {
        "n": n, "mean": avg, "min": min(times), "max": max(times),
        "stdev": sd, "median": sorted(times)[n // 2],
        "total": sum(times),
    }


def fmt_time(s):
    if s < 0.001:
        return f"{s*1e6:.0f}µs"
    if s < 1:
        return f"{s*1000:.1f}ms"
    return f"{s:.3f}s"


def cmd_run(args):
    n = args.n or 10
    warmup = args.warmup or 0

    if warmup:
        for _ in range(warmup):
            run_cmd(args.command)

    times = []
    for i in range(n):
        r = run_cmd(args.command)
        times.append(r["time"])
        if args.verbose:
            print(f"  Run {i+1}: {fmt_time(r['time'])}")

    s = stats(times)
    print(f"\n  Command: {args.command}")
    print(f"  Runs:    {s['n']}")
    print(f"  Mean:    {fmt_time(s['mean'])} ± {fmt_time(s['stdev'])}")
    print(f"  Min:     {fmt_time(s['min'])}")
    print(f"  Max:     {fmt_time(s['max'])}")
    print(f"  Median:  {fmt_time(s['median'])}")
    print(f"  Total:   {fmt_time(s['total'])}")

    # Histogram
    if n >= 5:
        buckets = 8
        lo, hi = s["min"], s["max"]
        if lo == hi:
            hi = lo + 0.001
        step = (hi - lo) / buckets
        hist = [0] * buckets
        for t in times:
            idx = min(int((t - lo) / step), buckets - 1)
            hist[idx] += 1
        mx = max(hist)
        print(f"\n  Distribution:")
        for i, count in enumerate(hist):
            bar = "█" * (count * 30 // mx) if mx else ""
            label = fmt_time(lo + i * step)
            print(f"    {label:>8} │{bar}")

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump({"command": args.command, "times": times, "stats": s}, f, indent=2)


def cmd_compare(args):
    results = []
    for cmd in args.commands:
        times = []
        for _ in range(args.n or 10):
            r = run_cmd(cmd)
            times.append(r["time"])
        s = stats(times)
        s["command"] = cmd
        results.append(s)

    results.sort(key=lambda x: x["mean"])
    baseline = results[0]["mean"]

    print(f"{'Command':<35} {'Mean':>10} {'±Stdev':>10} {'Min':>10} {'vs best':>10}")
    print("-" * 80)
    for r in results:
        ratio = r["mean"] / baseline if baseline else 0
        marker = " ⚡" if ratio == 1.0 else ""
        print(f"{r['command'][:34]:<35} {fmt_time(r['mean']):>10} {fmt_time(r['stdev']):>10} "
              f"{fmt_time(r['min']):>10} {ratio:>9.2f}x{marker}")


def cmd_profile(args):
    """Profile command over increasing input sizes."""
    sizes = [int(s) for s in args.sizes.split(",")]
    print(f"{'Size':>8} {'Time':>10} {'Rate':>12}")
    print("-" * 35)
    prev_time = None
    for size in sizes:
        cmd = args.command.replace("{N}", str(size))
        times = [run_cmd(cmd)["time"] for _ in range(args.n or 3)]
        avg = sum(times) / len(times)
        rate = size / avg if avg > 0 else 0
        growth = ""
        if prev_time and prev_time > 0:
            ratio = avg / prev_time
            growth = f"  ({ratio:.1f}x)"
        print(f"{size:>8} {fmt_time(avg):>10} {rate:>10.0f}/s{growth}")
        prev_time = avg


def main():
    p = argparse.ArgumentParser(description="Command benchmarking tool")
    sub = p.add_subparsers(dest="cmd")

    rp = sub.add_parser("run", help="Benchmark a command")
    rp.add_argument("command")
    rp.add_argument("-n", type=int, default=10)
    rp.add_argument("-w", "--warmup", type=int, default=0)
    rp.add_argument("-v", "--verbose", action="store_true")
    rp.add_argument("-o", "--json-output")

    cp = sub.add_parser("compare", help="Compare multiple commands")
    cp.add_argument("commands", nargs="+")
    cp.add_argument("-n", type=int, default=10)

    pp = sub.add_parser("profile", help="Profile with scaling input")
    pp.add_argument("command", help="Command with {N} placeholder")
    pp.add_argument("sizes", help="Comma-separated sizes")
    pp.add_argument("-n", type=int, default=3)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    {"run": cmd_run, "compare": cmd_compare, "profile": cmd_profile}[args.cmd](args)


if __name__ == "__main__":
    main()
