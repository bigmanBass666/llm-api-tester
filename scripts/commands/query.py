import os
import asyncio

from src import registry
from src.platform_config import PlatformConfigLoader
from src.platform_registry import ensure_platform_registered
from src.models import ModelType

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
    ensure_platform_registered(platform)
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
        print(f"{'#':<6}{'模型ID':<50}{'Owner'}")
        print("-" * 80)
        total = len(models)
        display_models = models[:50]
        for i, m in enumerate(display_models, 1):
            owner = f"[{m.scraped.api_owned_by}]" if (m.scraped and m.scraped.api_owned_by) else ""
            print(f"{i:<6}{m.id:<50}{owner}")
        if total > 50:
            print(f"\n共 {total} 个模型（仅显示前 50 个）")
        else:
            print(f"\n共 {total} 个模型")
    finally:
        client.close()

async def scrape_only(platform: str, number: int = 20, sort_by: str = "popular", model_type: str = "all", filter_text: bool = True, quiet: bool = False, usecase: str = None):
    ensure_platform_registered(platform)
    from src.platform_registry import get_platform_spec, create_component
    spec = get_platform_spec(platform)

    model_type_filter = None
    if model_type == "text":
        model_type_filter = ModelType.TEXT
    elif model_type == "image":
        model_type_filter = ModelType.IMAGE_GENERATION

    if spec and spec.legacy_mode:
        from crawler.scraper import scrape_top_models
        models = await scrape_top_models(limit=number, sort_by=sort_by, model_type_filter=model_type_filter, usecase_filter=usecase)
    elif spec and spec.scraper_cls:
        scraper = create_component(platform, "scraper")
        models = await scraper.scrape(limit=number, usecase_filter=usecase)
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
