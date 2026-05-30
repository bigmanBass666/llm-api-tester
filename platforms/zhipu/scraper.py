"""
智谱页面爬虫
由于智谱没有公开的模型浏览页面，使用预定义模型列表
"""

from typing import List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ModelInfo
from platforms.base.base_scraper import BaseScraper


class ZhipuScraper(BaseScraper):
    """智谱模型爬虫（使用预定义列表）"""

    platform_name = "zhipu"

    async def scrape(self, limit: int = 50, sort_by: str = "popular", sort_order: str = "DESC") -> List[ModelInfo]:
        """获取模型列表（智谱使用预定义列表，排序参数被忽略）"""
        from src.platform_config import PlatformConfigLoader

        scraper_config = PlatformConfigLoader.get_scraper_config(self.platform_name)
        known_models = scraper_config.known_models if scraper_config else []
        if not known_models:
            print(f"⚠️ 智谱: 未找到预定义模型列表，请检查 configs/platforms.yaml")
            return []

        print(f"🔍 智谱: 加载模型列表 (共 {len(known_models)} 个)")

        models = []
        for i, m in enumerate(known_models[:limit], 1):
            model = ModelInfo(
                id=m.get("model_id", m.get("name", f"unknown-{i}")),
                name=m.get("name", f"unknown-{i}"),
                vendor=m.get("vendor", "智谱"),
                rank=i,
                is_downloadable=False,
                is_free_endpoint=m.get("is_free", True),
                tags=["flash", "free"] if m.get("is_free", True) else []
            )
            models.append(model)
            print(f"\r[{i}/{len(known_models)}] {model.id}", end="", flush=True)

        print(f"\n✅ 智谱: 加载完成，共 {len(models)} 个模型")
        return models
