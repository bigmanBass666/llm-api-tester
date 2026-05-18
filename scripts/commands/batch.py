import os
import sys
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src import registry
from src.platform_registry import get_platform_spec, create_component, ensure_platform_registered, get_api_key
from src.models import ChatMessage, ModelType


async def run(platform, number=20, concurrency=5, timeout=60, sort_by="popular",
              model_type="all", scrape_only=False, resume=False, filter_text=True, quiet=False, usecase=None):
    ensure_platform_registered(platform)
    api_key = get_api_key(platform)
    spec = get_platform_spec(platform)
    config = registry.get(platform)
    display_name = (spec.display_name if spec and spec.display_name
                    else (config.display_name if config else platform))

    if not quiet:
        print(f"\n{'='*60}")
        print(f"  {display_name} 批量测试")
        print(f"{'='*60}")
        print(f"  模型数量 : {number}")
        print(f"  并发数   : {concurrency}")
        print(f"  超时时间 : {timeout}s")
        print(f"  排序方式 : {sort_by}")
        print(f"  模型类型 : {model_type}")
        if usecase:
            print(f"  用例过滤 : {usecase}")
        if scrape_only:
            print(f"  模式     : 仅爬取")
        print()

    model_type_filter = None
    if model_type == "text":
        model_type_filter = ModelType.TEXT
    elif model_type == "image":
        model_type_filter = ModelType.IMAGE_GENERATION

    if spec and spec.legacy_mode:
        from crawler.scraper import scrape_top_models
        models = await scrape_top_models(number, sort_by=sort_by,
                                         model_type_filter=model_type_filter,
                                         usecase_filter=usecase)
    elif spec and spec.scraper_cls is not None:
        scraper = create_component(platform, "scraper")
        models = await scraper.scrape(limit=number, usecase_filter=usecase)
    else:
        client = registry.create_client(platform, api_key=api_key)
        all_models = client.list_models()
        client.close()
        models = all_models[:number]

    if not models:
        if not quiet:
            print("无法获取模型列表")
        return

    # 用 API 数据丰富爬虫结果（NVIDIA 平台）
    if api_key and models and spec and spec.legacy_mode:
        try:
            from platforms.nvidia.client import NvidiaClient
            from platforms.nvidia.merger import merge_models
            api_client = NvidiaClient(api_key=api_key)
            api_models = api_client.list_models()
            api_client.close()
            models = merge_models(models, api_models)
            if not quiet:
                print(f"📡 API 数据合并完成: {len(models)} 个模型")
        except Exception as e:
            if not quiet:
                print(f"⚠️ API 数据合并失败: {e}")

    if not quiet:
        print(f"获取到 {len(models)} 个模型")

    if scrape_only:
        if not quiet:
            print("\n模型列表:")
            for m in models:
                tags = f" [{' '.join(m.tags)}]" if m.tags else ""
                print(f"  #{m.rank} {m.id}{tags}")
        return

    if not quiet:
        print(f"\n开始测试 ({concurrency} 并发)...")
        print("-" * 60)

    if spec and spec.legacy_mode:
        from crawler.tester import test_top_models
        await test_top_models(
            limit=number,
            concurrency=concurrency,
            use_logger=resume,
            resume=resume,
            sort_by=sort_by,
            filter_text_models=filter_text,
            reasoning_timeout=max(timeout * 3, 180),
        )
    else:
        tester = create_component(platform, "tester", api_key=api_key)
        results = await tester.batch_test(models, concurrency=concurrency,
                                          timeout=timeout)
        tester = None

        if results and not quiet:
            _print_summary(results, display_name)

        if results:
            try:
                from report.generator import ReportGenerator
                generator = ReportGenerator(platform=platform)
                files = generator.generate(results)
                if not quiet:
                    print(f"\n报告已生成:")
                    print(f"   Markdown: {files['markdown']}")
                    print(f"   JSON:     {files['json']}")
            except ImportError:
                pass


def _print_summary(results, platform_name):
    success = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    timeout_count = sum(1 for r in results if r.status == "timeout")
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  {platform_name} 测试摘要")
    print(f"{'='*60}")
    print(f"   总计  : {total}")
    print(f"   成功  : {success}")
    print(f"   失败  : {failed}")
    print(f"   超时  : {timeout_count}")
    if total > 0:
        print(f"   成功率: {success/total*100:.1f}%")

    fastest = sorted([r for r in results if r.status == "success"],
                     key=lambda x: x.response_time)
    if fastest:
        print(f"\n最快模型:")
        for r in fastest[:5]:
            print(f"   {r.model_id:<50} {r.response_time:.2f}s")
