"""
NVIDIA 爬虫兼容层 — 向后兼容的 re-export

外部调用方:
    from crawler.scraper import scrape_top_models    # ✓ 保留
    from crawler.scraper import fix_model_id         # ✓ 保留
"""

from src.models import ModelInfo

# 转发新版实现
from platforms.nvidia.scraper import scrape_top_models as _scrape_top_models
from src.models import ModelType


def fix_model_id(model_id: str) -> str:
    """将 NVIDIA 网页 ID 转换为 API 所需的 ID 格式"""
    return model_id.replace('_', '.')


async def scrape_top_models(limit: int = 50, sort_by: str = "popular",
                            filter_text_models: bool = False,
                            model_type_filter=None, usecase_filter=None) -> list:
    """爬取前N个热门模型（向后兼容的便捷函数）"""
    if model_type_filter is None and filter_text_models:
        model_type_filter = ModelType.TEXT
    return await _scrape_top_models(limit=limit, sort_by=sort_by,
                                    model_type_filter=model_type_filter,
                                    usecase_filter=usecase_filter)
