""" nemotron-3-ultra-550b-a55b 综合测评脚本

三大维度:
  1. 响应速度 — TTFT (Time To First Token) + 总耗时 + token 速率
  2. 稳定性   — 连续 N 轮调用,统计成功率、延迟分布(均值/中位数/P95)
  3. 并发压力 — 多并发同时请求,验证吞吐量 + 错误率

输出: reports/nemotron_3_ultra_comprehensive_<timestamp>.json
      控制台打印摘要
"""

import asyncio
import json
import statistics
import time
import os
import sys

# 确保项目根路径在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
import httpx

# ─── 配置 ────────────────────────────────────────────────
MODEL_ID = "nvidia/nemotron-3-ultra-550b-a55b"
API_KEY_ENV = "NVIDIA_API_KEY"
BASE_URL = "https://integrate.api.nvidia.com/v1"

SPEED_TEST_MESSAGE = "Please respond with exactly two words: Hello World"
STABILITY_MESSAGE = "What is 2+2? Reply with just the number."
CONCURRENCY_MESSAGE = "Reply OK"

SPEED_ROUNDS = 5
STABILITY_ROUNDS = 20
CONCURRENCY_LEVELS = [1, 3, 5, 10]

REQUEST_TIMEOUT = 60
# ─────────────────────────────────────────────────────────


# 共享异步 client（延迟初始化）
_async_client: httpx.AsyncClient = None


def _get_api_key():
    import dotenv
    dotenv.load_dotenv(".env.local")
    key = os.environ.get(API_KEY_ENV, "")
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith(f"{API_KEY_ENV}="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not key:
        print(f"[ERROR] 未找到 {API_KEY_ENV}")
        sys.exit(1)
    return key


def _make_sync_client(api_key):
    return OpenAI(
        base_url=BASE_URL,
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=REQUEST_TIMEOUT),
    )


async def _get_async_client(api_key):
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=REQUEST_TIMEOUT,
        )
    return _async_client


# ─── 维度 1: 响应速度 ───────────────────────────────────

def benchmark_speed(api_key) -> dict:
    """同步请求,测量平均响应时间 + token 生成速率"""
    print(f"\n{'='*60}")
    print(f" 维度 1: 响应速度 ({SPEED_ROUNDS} 轮)")
    print(f"{'='*60}")

    timings = []
    token_counts = []
    errors = []

    for i in range(SPEED_ROUNDS):
        client = _make_sync_client(api_key)
        tok_start = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": SPEED_TEST_MESSAGE}],
                max_tokens=128,
                temperature=0,
            )
            total_time = time.perf_counter() - tok_start
            content = resp.choices[0].message.content or ""
            usage = resp.usage
            tokens = (usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0)
            timings.append(total_time)
            token_counts.append(tokens[1] if tokens[1] > 0 else len(content.split()))
            print(f"  [{i+1}/{SPEED_ROUNDS}] {total_time:.3f}s | tokens≈{token_counts[-1]} | '{content[:40]}'")
        except Exception as e:
            errors.append(str(e)[:100])
            print(f"  [{i+1}/{SPEED_ROUNDS}] ❌ {e}")
        finally:
            client.close()

    if not timings:
        return {"error": "all requests failed", "errors": errors}

    return {
        "rounds": len(timings),
        "total_time_s": round(statistics.mean(timings), 4),
        "total_time_median_s": round(statistics.median(timings), 4),
        "total_time_min_s": round(min(timings), 4),
        "total_time_max_s": round(max(timings), 4),
        "total_time_stdev_s": round(statistics.stdev(timings), 4) if len(timings) > 1 else 0,
        "avg_tokens_per_sec": round(statistics.mean(token_counts) / statistics.mean(timings), 2) if timings and statistics.mean(timings) > 0 else 0,
        "errors": errors,
    }


# ─── 维度 2: 稳定性 ─────────────────────────────────────

async def _stable_request(api_key, round_num):
    client = _make_sync_client(api_key)
    start = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": STABILITY_MESSAGE}],
            max_tokens=32,
            temperature=0,
        )
        elapsed = time.perf_counter() - start
        content = resp.choices[0].message.content or ""
        usage = resp.usage
        tokens = (usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0)
        return {
            "round": round_num,
            "status": "success",
            "response_time": round(elapsed, 4),
            "tokens": tokens[1] if tokens[1] > 0 else len(content.split()),
            "response": content[:80],
            "error": None,
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "round": round_num,
            "status": "error",
            "response_time": round(elapsed, 4),
            "tokens": 0,
            "response": "",
            "error": str(e)[:120],
        }
    finally:
        client.close()


async def benchmark_stability(api_key) -> dict:
    """连续 N 轮调用,测量稳定性"""
    print(f"\n{'='*60}")
    print(f" 维度 2: 稳定性 ({STABILITY_ROUNDS} 轮连续请求)")
    print(f"{'='*60}")

    semaphore = asyncio.Semaphore(3)
    all_results = []

    async def guarded(n):
        async with semaphore:
            r = await _stable_request(api_key, n)
            all_results.append(r)
            status_icon = "✅" if r["status"] == "success" else "❌"
            print(f"  [{n:>2}/{STABILITY_ROUNDS}] {status_icon} {r['response_time']:.3f}s | {r['response'][:30]}")

    await asyncio.gather(*[guarded(i) for i in range(1, STABILITY_ROUNDS + 1)])

    successes = [r for r in all_results if r["status"] == "success"]
    failures = [r for r in all_results if r["status"] != "success"]

    stats = {}
    if successes:
        times = [r["response_time"] for r in successes]
        stats = {
            "success_rate": f"{len(successes)/STABILITY_ROUNDS*100:.1f}%",
            "success_count": len(successes),
            "failure_count": len(failures),
            "avg_time_s": round(statistics.mean(times), 4),
            "median_time_s": round(statistics.median(times), 4),
            "min_time_s": round(min(times), 4),
            "max_time_s": round(max(times), 4),
            "stdev_s": round(statistics.stdev(times), 4) if len(times) > 1 else 0,
            "p95_s": round(sorted(times)[int(len(times) * 0.95)], 4),
            "p99_s": round(sorted(times)[int(len(times) * 0.99)], 4),
        }

    error_types = {}
    for f in failures:
        key = f["error"][:30]
        error_types[key] = error_types.get(key, 0) + 1

    return {
        "total_rounds": STABILITY_ROUNDS,
        **stats,
        "error_types": error_types,
        "failure_details": failures[:10],
    }


# ─── 维度 3: 并发压力 ───────────────────────────────────

async def _concurrent_request(api_key, request_id):
    client = httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=REQUEST_TIMEOUT,
    )
    start = time.perf_counter()
    try:
        resp = await client.post(
            "/chat/completions",
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": CONCURRENCY_MESSAGE}],
                "max_tokens": 16,
                "temperature": 0,
            },
        )
        elapsed = time.perf_counter() - start
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"] or ""
            return {
                "id": request_id,
                "status": "success",
                "response_time": round(elapsed, 4),
                "error": None,
            }
        else:
            return {
                "id": request_id,
                "status": "error",
                "response_time": round(elapsed, 4),
                "error": f"HTTP {resp.status_code}: {resp.text[:80]}",
            }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "id": request_id,
            "status": "error",
            "response_time": round(elapsed, 4),
            "error": str(e)[:120],
        }
    finally:
        await client.aclose()


async def benchmark_concurrency(api_key) -> dict:
    """不同并发级别下的吞吐量和错误率"""
    print(f"\n{'='*60}")
    print(f" 维度 3: 并发压力 (levels: {CONCURRENCY_LEVELS})")
    print(f"{'='*60}")

    results = {}

    for level in CONCURRENCY_LEVELS:
        print(f"\n  --- 并发={level} ---")
        semaphore = asyncio.Semaphore(level)
        reqs = []

        async def run(n):
            async with semaphore:
                return await _concurrent_request(api_key, n)

        wall_start = time.perf_counter()
        batch = await asyncio.gather(*[run(i) for i in range(level)])
        wall_time = time.perf_counter() - wall_start

        success = [r for r in batch if r["status"] == "success"]
        failed = [r for r in batch if r["status"] != "success"]

        if success:
            times = [r["response_time"] for r in success]
            throughput = len(success) / wall_time if wall_time > 0 else 0
            level_stats = {
                "total_requests": len(batch),
                "success": len(success),
                "failed": len(failed),
                "success_rate": f"{len(success)/level*100:.1f}%",
                "wall_time_s": round(wall_time, 4),
                "throughput_rps": round(throughput, 4),
                "avg_latency_s": round(statistics.mean(times), 4),
                "median_latency_s": round(statistics.median(times), 4),
                "min_latency_s": round(min(times), 4),
                "max_latency_s": round(max(times), 4),
            }
        else:
            level_stats = {
                "total_requests": len(batch),
                "success": 0,
                "failed": len(failed),
                "success_rate": "0%",
                "wall_time_s": round(wall_time, 4),
                "throughput_rps": 0,
            }

        results[f"concurrency_{level}"] = level_stats
        icon = "✅" if level_stats.get("success", 0) == level else "⚠️"
        print(f"  {icon} 成功={len(success)}/{level} | 吞吐={level_stats.get('throughput_rps', 0)} rps | 耗时={level_stats['wall_time_s']}s")

    return results


# ─── 报告生成 ───────────────────────────────────────────

def generate_report(speed, stability, concurrency, wall_total):
    """打印摘要 + 保存 JSON"""
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(report_dir, exist_ok=True)
    json_path = os.path.join(report_dir, f"nemotron_3_ultra_comprehensive_{ts}.json")

    report = {
        "model": MODEL_ID,
        "timestamp": ts,
        "total_duration_s": round(wall_total, 2),
        "dimension_1_speed": speed,
        "dimension_2_stability": stability,
        "dimension_3_concurrency": concurrency,
    }

    # ── 控制台摘要 ──
    print(f"\n{'='*60}")
    print(f" 综合测评摘要 — {MODEL_ID}")
    print(f"{'='*60}")

    if "total_time_s" in speed:
        print(f"\n【响应速度】")
        print(f"  平均耗时:  {speed['total_time_s']}s")
        print(f"  中位数:    {speed['total_time_median_s']}s")
        print(f"  最快:      {speed['total_time_min_s']}s")
        print(f"  最慢:      {speed['total_time_max_s']}s")
        print(f"  标准差:    {speed['total_time_stdev_s']}s")
        print(f"  生成速度:  {speed['avg_tokens_per_sec']} tok/s")
        if speed["errors"]:
            print(f"  错误:      {len(speed['errors'])}/{SPEED_ROUNDS}")

    if "success_rate" in stability:
        print(f"\n【稳定性】({stability['total_rounds']} 轮)")
        print(f"  成功率:    {stability['success_rate']}")
        print(f"  平均延迟:  {stability['avg_time_s']}s")
        print(f"  中位数:    {stability['median_time_s']}s")
        print(f"  P95:       {stability['p95_s']}s")
        print(f"  P99:       {stability['p99_s']}s")

    if concurrency:
        print(f"\n【并发压力】")
        for level, s in concurrency.items():
            print(f"  {level}: 成功={s.get('success',0)}/{s['total_requests']} | 吞吐={s.get('throughput_rps',0)} rps | avg={s.get('avg_latency_s','N/A')}s")

    print(f"\n└─ 总测试耗时: {wall_total:.1f}s")
    print(f"└─ JSON: {json_path}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return json_path


# ─── 入口 ───────────────────────────────────────────────

async def main():
    print(f"\n{'='*60}")
    print(f" {MODEL_ID} 综合测评")
    print(f"{'='*60}")

    api_key = _get_api_key()

    # 快速连接验证
    try:
        _make_sync_client(api_key).models.retrieve(MODEL_ID)
        print(f"✅ 连接成功,模型存在: {MODEL_ID}\n")
    except Exception as e:
        print(f"⚠️ 连接验证异常(可能模型不存在): {e}\n")

    wall_total_start = time.perf_counter()

    # 维度 1: 同步速度测试
    speed = benchmark_speed(api_key)

    # 维度 2: 异步稳定性测试
    stability = await benchmark_stability(api_key)

    # 维度 3: 并发压力测试
    concurrency = await benchmark_concurrency(api_key)

    wall_total = time.perf_counter() - wall_total_start

    # 报告
    json_path = generate_report(speed, stability, concurrency, wall_total)


if __name__ == "__main__":
    asyncio.run(main())
