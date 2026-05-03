import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src import registry
from src.platform_config import PlatformConfigLoader


def list_platforms():
    configs = PlatformConfigLoader.load_all()
    available = {k: v for k, v in configs.items() if v.is_available}
    print("可用平台:")
    print(f"{'名称':<12}{'显示名':<20}{'API Key 环境变量':<24}{'状态'}")
    print("-" * 68)
    for name, cfg in available.items():
        key_env = cfg.api_key_env
        if not key_env:
            env_display = "-"
            status = "\u274c"
        else:
            env_display = key_env
            status = "\u2705" if os.getenv(key_env) else "\u274c"
        print(f"{name:<12}{cfg.display_name:<20}{env_display:<24}{status}")


async def list_models(platform: str):
    _ensure_platform_registered(platform)
    config = registry.get(platform)
    if not config:
        raise ValueError(f"未知平台: {platform}")
    api_key_env = config.api_key_env
    if not api_key_env:
        raise ValueError(f"平台 {platform} 未配置 API Key 环境变量")
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"环境变量 {api_key_env} 未设置，请先配置 API Key")
    client = registry.create_client(platform, api_key=api_key)
    try:
        display_name = config.display_name
        models = client.list_models()
        print(f"\n{display_name} 可用模型:")
        print(f"{'#':<6}{'模型ID':<50}{'名称'}")
        print("-" * 90)
        total = len(models)
        display_models = models[:50]
        for i, m in enumerate(display_models, 1):
            print(f"{i:<6}{m.id:<50}{m.name}")
        if total > 50:
            print(f"\n共 {total} 个模型（仅显示前 50 个）")
        else:
            print(f"\n共 {total} 个模型")
    finally:
        client.close()


async def scrape_only(platform: str, number: int = 20, sort_by: str = "popular", filter_text: bool = True, quiet: bool = False):
    _ensure_platform_registered(platform)
    from src.platform_registry import get_platform_spec, create_component
    spec = get_platform_spec(platform)
    if spec is None:
        raise ValueError(f"平台 {platform} 无可用规格")

    if spec.legacy_mode:
        from crawler.scraper import scrape_top_models
        models = await scrape_top_models(limit=number, sort_by=sort_by, filter_text_models=filter_text)
    elif spec.scraper_cls:
        scraper = create_component(platform, "scraper")
        models = await scraper.scrape(limit=number)
    else:
        config = registry.get(platform)
        api_key_env = config.api_key_env
        if not api_key_env:
            raise ValueError(f"平台 {platform} 未配置 API Key 环境变量")
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"环境变量 {api_key_env} 未设置，请先配置 API Key")
        client = registry.create_client(platform, api_key=api_key)
        try:
            models = client.list_models()[:number]
        finally:
            client.close()

    print(f"\n{'排名':<6}{'模型ID':<50}{'标签'}")
    print("-" * 90)
    for i, m in enumerate(models, 1):
        tags = ", ".join(m.tags) if m.tags else ""
        print(f"{i:<6}{m.id:<50}{tags}")
    print(f"\n共 {len(models)} 个模型")


def _ensure_platform_registered(platform: str):
    """确保平台 client 已注册到 registry"""
    if registry.get(platform) is not None:
        return
    try:
        import importlib
        importlib.import_module(f"platforms.{platform}.client")
    except (ImportError, ModuleNotFoundError):
        pass
