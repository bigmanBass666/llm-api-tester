"""
统一测试入口（CLI 薄壳）
所有业务逻辑在 scripts/commands/ 中，本文件只做参数解析 + 路由

用法:
  python scripts/batch_test.py -m meta/llama-3.3-70b-instruct
  python scripts/batch_test.py -m glm-4-flash -p zhipu --message "你好"
  python scripts/batch_test.py -p nvidia -n 20
  python scripts/batch_test.py --list
  python scripts/batch_test.py -p nvidia --list-models
  python scripts/batch_test.py -p nvidia --scrape-only -n 20
"""

import sys
import os
import asyncio
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import registry
from src.config_loader import ConfigLoader


def _get_platform_choices():
    ConfigLoader.load_env(".env.local")
    try:
        from src.platform_config import PlatformConfigLoader
        return PlatformConfigLoader.get_available_platforms()
    except Exception:
        pass
    return [p.name for p in registry.list_available_platforms()]


def main():
    platform_choices = _get_platform_choices()

    parser = argparse.ArgumentParser(
        description="AI 模型统一测试工具 — 单模型 / 批量 / 爬取 / 报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/batch_test.py -m meta/llama-3.3-70b-instruct
  python scripts/batch_test.py -m glm-4-flash -p zhipu --message "你好"
  python scripts/batch_test.py -p nvidia -n 20
  python scripts/batch_test.py -p zhipu -n 10
  python scripts/batch_test.py --list
  python scripts/batch_test.py -p nvidia --list-models
  python scripts/batch_test.py -p nvidia --scrape-only -n 20
  python scripts/batch_test.py -p nvidia -n 20 -c 5 --sort-by recent
        """
    )

    core = parser.add_argument_group("核心参数")
    core.add_argument("--platform", "-p", choices=platform_choices,
                      help="目标平台")
    core.add_argument("--model", "-m", metavar="MODEL_ID",
                      help="测试单个模型（完整模型 ID）")
    core.add_argument("-n", "--number", type=int, default=20,
                      help="批量测试的模型数量 (默认: 20)")

    query = parser.add_argument_group("查询模式")
    query.add_argument("--list", "-l", action="store_true",
                       help="列出所有可用平台及 API Key 状态")
    query.add_argument("--list-models", action="store_true",
                       help="列出指定平台的可用模型（需配合 -p）")
    query.add_argument("--scrape-only", action="store_true",
                       help="仅爬取模型列表，不执行测试（需配合 -p -n）")

    opts = parser.add_argument_group("测试选项")
    opts.add_argument("--message", default="请回复'OK'",
                      help="单模型测试时的消息内容")
    opts.add_argument("-c", "--concurrency", type=int, default=5,
                      help="并发测试数量 (默认: 5)")
    opts.add_argument("--timeout", type=int, default=60,
                      help="单个模型超时时间(秒) (默认: 60)")
    opts.add_argument("--max-time", type=int, default=0,
                      help="总测试时间上限(秒)，0=不限制 (默认: 0)")
    opts.add_argument("--sort-by", default="popular",
                      choices=["popular", "recent"],
                      help="排序方式 (默认: popular)")
    opts.add_argument("--model-type", default="all",
                      choices=["text", "image", "all"],
                      help="模型类型过滤 (默认: all)")
    opts.add_argument("--usecase", default=None,
                      help="用例过滤 (如 text-generation, image-generation, embedding 等)")

    adv = parser.add_argument_group("高级选项")
    adv.add_argument("--resume", action="store_true",
                     help="断点续传（跳过已测试的模型，仅 NVIDIA）")
    adv.add_argument("--no-filter", action="store_true",
                     help="禁用非文字模型过滤")
    adv.add_argument("--quiet", "-q", action="store_true",
                     help="安静模式，减少输出")
    adv.add_argument("--probe-hosted", action="store_true",
                     help="探测哪些模型真正有托管端点（发送最小 chat 请求）")

    args = parser.parse_args()

    from commands import run_single as single_test, batch, query

    if args.list:
        query.list_platforms()

    elif args.model:
        single_test.run(
            model_id=args.model,
            platform=args.platform or "nvidia",
            message=args.message,
            verbose=not args.quiet,
        )

    elif args.list_models:
        if not args.platform:
            parser.error("--list-models 需要配合 -p 指定平台")
        asyncio.run(query.list_models(args.platform))

    elif args.scrape_only:
        if not args.platform:
            parser.error("--scrape-only 需要配合 -p 指定平台")
        asyncio.run(query.scrape_only(
            platform=args.platform,
            number=args.number,
            sort_by=args.sort_by,
            model_type=args.model_type,
            filter_text=not args.no_filter,
            quiet=args.quiet,
            usecase=args.usecase,
        ))

    elif args.probe_hosted:
        ConfigLoader.load_env(".env.local")
        asyncio.run(_probe_hosted_models(args.number))

    elif args.platform:
        asyncio.run(batch.run(
            platform=args.platform,
            number=args.number,
            concurrency=args.concurrency,
            timeout=args.timeout,
            max_time=args.max_time,
            sort_by=args.sort_by,
            model_type=args.model_type,
            resume=args.resume,
            filter_text=not args.no_filter,
            quiet=args.quiet,
            usecase=args.usecase,
        ))

    else:
        print("未指定参数，运行默认模式: NVIDIA 批量测试")
        print("   使用 -h 查看完整用法\n")
        asyncio.run(batch.run(platform="nvidia", number=20, concurrency=5))


async def _probe_hosted_models(limit: int):
    from platforms.nvidia.model_prober import NvidiaModelProber
    from platforms.nvidia.client import NvidiaClient
    from src.platform_registry import get_api_key

    api_key = get_api_key("nvidia")
    if not api_key:
        print("❌ 未找到 NVIDIA API Key，请检查 .env.local")
        return

    print(f"📡 获取模型列表（前 {limit} 个）...")
    client = NvidiaClient(api_key=api_key)
    models = client.list_models()[:limit]
    client.close()

    print(f"🔍 开始探测 {len(models)} 个模型的可用性...")
    prober = NvidiaModelProber(api_key=api_key)

    def progress(done, total, mid, is_hosted):
        icon = "✅" if is_hosted else "❌"
        print(f"  [{done}/{total}] {icon} {mid}")

    results = await prober.probe_batch(
        [m.id for m in models],
        concurrency=10,
        progress_callback=progress,
    )

    hosted = sum(1 for v in results.values() if v[0])
    print(f"\n📊 结果: {hosted}/{len(results)} 个模型有可用的 chat 端点")


if __name__ == "__main__":
    main()
