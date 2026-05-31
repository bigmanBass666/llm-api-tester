import os
import time
import asyncio
import yaml
from typing import List, Optional

from src import registry
from src.platform_registry import get_platform_spec, create_component, ensure_platform_registered, get_api_key
from src.models import ChatMessage, ModelInfo, ModelType

async def run(platform, number=20, concurrency=5, timeout=30, max_time=0, sort_by="popular",
              model_type="all", scrape_only=False, resume=False, filter_text=True, quiet=False,
              usecase=None, favorites=False,
              use_logger=True, reasoning_timeout=180, force_reasoning=False,
              force_normal=False, manual_reasoning_models=None):
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
        if max_time > 0:
            print(f"  总时间上限 : {max_time}s")
        print(f"  排序方式 : {sort_by}")
        print(f"  模型类型 : {model_type}")
        if usecase:
            print(f"  用例过滤 : {usecase}")
        if scrape_only:
            print(f"  模式     : 仅爬取")
        print()

    # 阶段 1: 获取模型
    models = await _gather_models(
        platform=platform, spec=spec, api_key=api_key,
        number=number, sort_by=sort_by, model_type=model_type,
        usecase=usecase, favorites=favorites, quiet=quiet,
    )

    if not models:
        if not quiet:
            print("无法获取模型列表")
        return

    # 过滤 API 中不存在的模型（收藏模式跳过）
    if not favorites:
        before_count = len(models)
        models = [m for m in models if (m.scraped.is_hosted if m.scraped else True)]
        if not quiet and before_count > len(models):
            skipped = before_count - len(models)
            print(f"🚫 已跳过 {skipped} 个 API 不可用的模型")

    if scrape_only:
        if not quiet:
            print("\n模型列表:")
            for m in models:
                tags = f" [{' '.join(m.tags)}]" if m.tags else ""
                s = m.scraped
                api = " 🌐" if s and s.is_hosted else " ❌" if s and s.is_hosted is False else ""
                print(f"  #{m.rank} {m.id}{tags}{api}")
        return

    # 阶段 2: 执行测试
    await _run_testing(
        platform=platform, spec=spec, models=models, api_key=api_key,
        display_name=display_name,
        number=number, concurrency=concurrency, timeout=timeout,
        max_time=max_time, sort_by=sort_by,
        resume=resume, filter_text=filter_text, quiet=quiet,
        favorites=favorites,
        use_logger=use_logger, reasoning_timeout=reasoning_timeout,
        force_reasoning=force_reasoning, force_normal=force_normal,
        manual_reasoning_models=manual_reasoning_models,
    )

async def _gather_models(
    platform: str, spec, api_key: str,
    number: int, sort_by: str, model_type: str,
    usecase: Optional[str], favorites: bool, quiet: bool,
) -> List[ModelInfo]:
    """阶段 1: 获取并合并模型列表（爬取 / API / 收藏）"""
    model_type_filter = None
    if model_type == "text":
        model_type_filter = ModelType.TEXT
    elif model_type == "image":
        model_type_filter = ModelType.IMAGE_GENERATION

    # 收藏模型模式
    if favorites:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'platforms.yaml')
        with open(config_path) as f:
            all_configs = yaml.safe_load(f)
        platform_config = all_configs.get('platforms', {}).get(platform, {})
        fav_ids = platform_config.get('favorites', [])
        if not fav_ids:
            print("⚠️ 未配置收藏模型，请在 platforms.yaml 中添加 favorites 字段")
            return []
        if not quiet:
            print(f"⭐ 收藏模型模式: {len(fav_ids)} 个模型")
        client = registry.create_client(platform, api_key=api_key)
        all_models = client.list_models()
        client.close()
        models = [m for m in all_models if m.id in fav_ids]
        order = {mid: i for i, mid in enumerate(fav_ids)}
        models.sort(key=lambda m: order.get(m.id, 999))
        return models

    # 爬取 / API 获取
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
        return []

    # 用 API 数据丰富爬虫结果（NVIDIA legacy 模式）
    if api_key and spec and spec.legacy_mode:
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

    return models

async def _run_testing(
    platform: str, spec, models: List[ModelInfo], api_key: str, display_name: str,
    number: int, concurrency: int, timeout: int, max_time: int,
    sort_by: str, resume: bool, filter_text: bool, quiet: bool, favorites: bool,
    use_logger: bool = True, reasoning_timeout: int = 180,
    force_reasoning: bool = False, force_normal: bool = False,
    manual_reasoning_models: list = None,
):
    """阶段 2: 执行测试并生成报告"""
    if not quiet:
        print(f"\n开始测试 ({concurrency} 并发)...")
        print("-" * 60)

    # Legacy 路径（NVIDIA 爬虫+测试器一体化）
    if spec and spec.legacy_mode and not favorites:
        from crawler.tester import test_top_models
        effective_reasoning_timeout = reasoning_timeout if reasoning_timeout != 180 else max(timeout * 3, 180)
        test_kwargs = dict(
            limit=number, concurrency=concurrency,
            use_logger=use_logger or resume, resume=resume, sort_by=sort_by,
            filter_text_models=filter_text,
            reasoning_timeout=effective_reasoning_timeout,
            force_reasoning=force_reasoning,
            force_normal=force_normal,
            manual_reasoning_models=manual_reasoning_models,
        )
        try:
            if max_time > 0:
                if not quiet:
                    print(f"⏱️ 总时间限制: {max_time}s")
                await asyncio.wait_for(test_top_models(**test_kwargs), timeout=max_time)
            else:
                await test_top_models(**test_kwargs)
        except asyncio.TimeoutError:
            if not quiet:
                print(f"\n⏰ 总时间已达 {max_time}s 上限，提前结束测试")
        return

    # 新路径（平台 Tester 组件）
    tester = create_component(platform, "tester", api_key=api_key)
    results = await tester.batch_test(models, concurrency=concurrency, timeout=timeout)
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
