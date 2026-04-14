#!/usr/bin/env python3
"""
load_test.py — Hari WebSocket Load Test
─────────────────────────────────────────
Simulates N concurrent users connecting to the live WS server,
each sending a fixed prompt and measuring TTFT + total latency.

NOT a Locust file — runs standalone with asyncio so it works on Windows
without needing a Locust web UI. For larger runs, see comments below.

Usage:
    # Quick check — 1 user
    python eval/load_test.py --users 1 --url wss://chatting-hari.com/ws/chat/

    # Ramp test — 10 concurrent users
    python eval/load_test.py --users 10 --url wss://chatting-hari.com/ws/chat/ \
        --username TEST_USER --password TEST_PASS

    # Stress test — ramp from 1 to N, find breaking point
    python eval/load_test.py --ramp --max-users 50 --step 5 --step-duration 30 \
        --username TEST_USER --password TEST_PASS

Requirements:
    pip install websockets httpx
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx
import websockets

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_WS_URL    = "wss://chatting-hari.com/ws/chat/"
DEFAULT_LOGIN_URL = "https://chatting-hari.com/api/chat/login/"
WS_TIMEOUT        = 30.0

# Prompts used in load test — kept short, realistic
LOAD_PROMPTS = [
    "오늘 핫한 AI 뉴스 뭐야?",
    "엔비디아 요즘 어때?",
    "요즘 뭐 만들어?",
    "챗GPT 어때?",
    "테슬라 자율주행 어디까지 왔어?",
    "좋아하는 유튜버 있어?",
    "오늘 기분 어때?",
    "아이폰이랑 갤럭시 중에 뭐 써?",
]


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_session_cookie(login_url: str, username: str, password: str) -> dict[str, str]:
    with httpx.Client(follow_redirects=True) as client:
        resp = client.get(login_url)
        resp.raise_for_status()
        csrf = resp.cookies.get("csrftoken", "")
        if not csrf:
            m = re.search(r'csrfmiddlewaretoken.*?value="([^"]+)"', resp.text)
            csrf = m.group(1) if m else ""

        resp = client.post(
            login_url,
            data={"username": username, "password": password, "csrfmiddlewaretoken": csrf},
            headers={"Referer": login_url},
        )
        cookies = dict(client.cookies)
        if "sessionid" not in cookies:
            raise RuntimeError(f"Login failed (status {resp.status_code}). Check credentials.")
        return cookies


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class UserResult:
    user_id: int
    prompt: str
    ttft: float | None = None       # time to first token (seconds)
    total_latency: float | None = None
    response_len: int = 0
    error: str | None = None
    success: bool = False


# ── Virtual user ──────────────────────────────────────────────────────────────

async def virtual_user(
    user_id: int,
    ws_url: str,
    cookies: dict[str, str],
    prompt: str,
    timeout: float = WS_TIMEOUT,
) -> UserResult:
    result = UserResult(user_id=user_id, prompt=prompt)
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

    try:
        t_start = time.perf_counter()
        async with websockets.connect(
            ws_url,
            additional_headers={"Cookie": cookie_header},
            open_timeout=10,
        ) as ws:
            # Drain opening message if any
            try:
                await asyncio.wait_for(ws.recv(), timeout=5.0)
            except asyncio.TimeoutError:
                pass

            t_send = time.perf_counter()
            await ws.send(json.dumps({"message": prompt}))

            chunks: list[str] = []
            ttft_recorded = False
            deadline = time.perf_counter() + timeout

            while time.perf_counter() < deadline:
                remaining = deadline - time.perf_counter()
                inner_timeout = min(remaining, 3.0 if ttft_recorded else timeout)
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=inner_timeout)
                    data = json.loads(raw)
                    chunk = data.get("message", "") or data.get("chunk", "")
                    if chunk:
                        if not ttft_recorded:
                            result.ttft = time.perf_counter() - t_send
                            ttft_recorded = True
                        chunks.append(chunk)
                    if data.get("done") or data.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    if ttft_recorded:
                        break  # silence after first message = done

            result.total_latency = time.perf_counter() - t_send
            result.response_len = len("".join(chunks))
            result.success = ttft_recorded and result.response_len > 0

    except Exception as e:
        result.error = str(e)
        result.total_latency = time.perf_counter() - (result.ttft or time.perf_counter())

    return result


# ── Load runner ───────────────────────────────────────────────────────────────

async def run_concurrent(
    ws_url: str,
    cookies: dict[str, str],
    n_users: int,
    stagger_ms: int = 200,
) -> list[UserResult]:
    """Spawn n_users virtual users with a small stagger between each."""
    tasks = []
    for i in range(n_users):
        prompt = LOAD_PROMPTS[i % len(LOAD_PROMPTS)]
        if stagger_ms > 0 and i > 0:
            await asyncio.sleep(stagger_ms / 1000)
        tasks.append(asyncio.create_task(virtual_user(i + 1, ws_url, cookies, prompt)))
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)


async def run_ramp(
    ws_url: str,
    cookies: dict[str, str],
    max_users: int,
    step: int,
    step_duration: int,
) -> dict[int, list[UserResult]]:
    """Ramp from `step` to `max_users` in increments of `step`."""
    ramp_results: dict[int, list[UserResult]] = {}
    for n in range(step, max_users + 1, step):
        print(f"\n  ── Ramp step: {n} concurrent users ──")
        batch = await run_concurrent(ws_url, cookies, n)
        ramp_results[n] = batch
        _print_batch_summary(batch, n)
        if n < max_users:
            print(f"  Waiting {step_duration}s before next step...")
            await asyncio.sleep(step_duration)
    return ramp_results


# ── Stats ─────────────────────────────────────────────────────────────────────

def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    return sorted_v[min(idx, len(sorted_v) - 1)]


def _print_batch_summary(results: list[UserResult], n_users: int) -> None:
    successes = [r for r in results if r.success]
    errors = [r for r in results if not r.success]
    success_rate = len(successes) / len(results) * 100 if results else 0

    ttfts = [r.ttft for r in successes if r.ttft is not None]
    latencies = [r.total_latency for r in successes if r.total_latency is not None]

    print(f"  Users: {n_users}  |  Success: {len(successes)}/{len(results)} ({success_rate:.0f}%)")
    if ttfts:
        print(f"  TTFT  — p50: {percentile(ttfts, 50):.2f}s  p95: {percentile(ttfts, 95):.2f}s  max: {max(ttfts):.2f}s")
    if latencies:
        print(f"  Total — p50: {percentile(latencies, 50):.2f}s  p95: {percentile(latencies, 95):.2f}s  max: {max(latencies):.2f}s")
    if errors:
        print(f"  Errors ({len(errors)}):")
        for r in errors[:5]:
            print(f"    User {r.user_id}: {r.error}")


def print_final_report(all_results: list[UserResult], mode: str, n_users: int) -> None:
    w = 65
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print("=" * w)
    print(f"  HARI LOAD TEST REPORT — {now}")
    print(f"  Mode: {mode}  |  Peak users: {n_users}")
    print("=" * w)

    successes = [r for r in all_results if r.success]
    errors = [r for r in all_results if not r.success]
    ttfts = [r.ttft for r in successes if r.ttft]
    latencies = [r.total_latency for r in successes if r.total_latency]

    print(f"\n  Total requests:  {len(all_results)}")
    print(f"  Successes:       {len(successes)} ({len(successes)/len(all_results)*100:.0f}%)")
    print(f"  Errors:          {len(errors)}")

    if ttfts:
        print(f"\n  TTFT (Time To First Token)")
        print(f"  p50:  {percentile(ttfts, 50):.3f}s")
        print(f"  p95:  {percentile(ttfts, 95):.3f}s")
        print(f"  p99:  {percentile(ttfts, 99):.3f}s")
        print(f"  max:  {max(ttfts):.3f}s")

    if latencies:
        print(f"\n  End-to-End Latency")
        print(f"  p50:  {percentile(latencies, 50):.3f}s")
        print(f"  p95:  {percentile(latencies, 95):.3f}s")
        print(f"  p99:  {percentile(latencies, 99):.3f}s")
        print(f"  max:  {max(latencies):.3f}s")

    if errors:
        print(f"\n  Error breakdown:")
        error_types: dict[str, int] = {}
        for r in errors:
            key = (r.error or "unknown")[:60]
            error_types[key] = error_types.get(key, 0) + 1
        for err, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"    [{count}x] {err}")

    # SLO check
    # Thresholds are intentionally relaxed: Hari is a human persona, not a
    # streaming API. A 3-6s response time feels natural and deliberate.
    print(f"\n  SLO ASSESSMENT  (human-pacing targets)")
    slo_ttft_p50  = percentile(ttfts, 50) <= 6.0  if ttfts else False
    slo_ttft_p95  = percentile(ttfts, 95) <= 12.0 if ttfts else False
    slo_lat_p95   = percentile(latencies, 95) <= 18.0 if latencies else False
    slo_error     = (len(errors) / len(all_results)) <= 0.005 if all_results else False
    for label, passed in [
        ("TTFT p50 < 6.0s  (human pacing)", slo_ttft_p50),
        ("TTFT p95 < 12.0s (human pacing)", slo_ttft_p95),
        ("E2E  p95 < 18.0s", slo_lat_p95),
        ("Error rate < 0.5%", slo_error),
    ]:
        icon = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
        print(f"  {icon}  {label}")

    print()
    print("=" * w)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Hari WebSocket load test")
    parser.add_argument("--url", default=DEFAULT_WS_URL)
    parser.add_argument("--login-url", default=DEFAULT_LOGIN_URL)
    parser.add_argument("--username", default=os.environ.get("HARI_TEST_USER"))
    parser.add_argument("--password", default=os.environ.get("HARI_TEST_PASS"))
    parser.add_argument("--users", type=int, default=1, help="Concurrent users (fixed mode)")
    parser.add_argument("--stagger-ms", type=int, default=200, help="ms between user spawns")
    parser.add_argument("--ramp", action="store_true", help="Ramp mode: gradually increase users")
    parser.add_argument("--max-users", type=int, default=30, help="Max users in ramp mode")
    parser.add_argument("--step", type=int, default=5, help="User increment per ramp step")
    parser.add_argument("--step-duration", type=int, default=30, help="Seconds per ramp step")
    parser.add_argument("--output", help="Save raw results to JSON file")
    args = parser.parse_args()

    # Auth
    cookies: dict[str, str] = {}
    if args.username and args.password:
        print(f"  Logging in as '{args.username}'...")
        cookies = get_session_cookie(args.login_url, args.username, args.password)
        print("  Login successful.")
    else:
        print("  WARNING: No credentials — guest mode may be rejected in production.")

    if args.ramp:
        ramp_data = asyncio.run(run_ramp(
            args.url, cookies, args.max_users, args.step, args.step_duration
        ))
        all_results = [r for batch in ramp_data.values() for r in batch]
        print_final_report(all_results, "ramp", args.max_users)
    else:
        print(f"\n  Starting {args.users} concurrent user(s)...")
        results = asyncio.run(run_concurrent(args.url, cookies, args.users, args.stagger_ms))
        print_final_report(results, "fixed", args.users)

    if args.output:
        out = {
            "run_at": datetime.now().isoformat(),
            "ws_url": args.url,
            "mode": "ramp" if args.ramp else "fixed",
            "results": [
                {
                    "user_id": r.user_id,
                    "prompt": r.prompt,
                    "ttft": r.ttft,
                    "total_latency": r.total_latency,
                    "response_len": r.response_len,
                    "success": r.success,
                    "error": r.error,
                }
                for r in (all_results if args.ramp else results)
            ],
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"  Raw results → {args.output}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
