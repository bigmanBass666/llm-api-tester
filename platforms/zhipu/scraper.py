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

    KNOWN_MODELS = [
        ("glm-4-flash", "glm-4-flash-250414", "智谱", True),
        ("glm-4v-flash", "glm-4v-flash", "智谱", True),
        ("glm-4.7-flash", "glm-4.7-flash", "智谱", True),
        ("glm-4.1v-thinking-flash", "glm-4.1v-thinking-flash", "智谱", True),
        ("cogview-3-flash", "cogview-3-flash", "智谱", True),
        ("cogvideox-flash", "cogvideox-flash", "智谱", True),
        ("glm-4.6v-flash", "glm-4.6v-flash", "智谱", True),
    ]

    async def scrape(self, limit: int = 50) -> List[ModelInfo]:
        """获取模型列表"""
        print(f"🔍 智谱: 加载模型列表 (共 {len(self.KNOWN_MODELS)} 个)")

        models = []
        for i, (name, model_id, vendor, is_free) in enumerate(self.KNOWN_MODELS, 1):
            if i > limit:
                break

            model = ModelInfo(
                id=model_id,
                name=name,
                vendor=vendor,
                rank=i,
                is_downloadable=False,
                is_free_endpoint=is_free,
                tags=["flash", "free"] if is_free else []
            )
            models.append(model)
            print(f"\r[{i}/{len(self.KNOWN_MODELS)}] {model_id}", end="", flush=True)

        print(f"\n✅ 智谱: 加载完成，共 {len(models)} 个模型")
        return models