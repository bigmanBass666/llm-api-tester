"""
NVIDIA 模型数据合并器
将爬虫数据和 API 数据合并为统一的 ModelInfo
"""

from typing import List, Dict
from src.models import ModelInfo, ScrapedMetadata


def build_api_index(api_models: List[ModelInfo]) -> Dict[str, ModelInfo]:
    return {m.id: m for m in api_models}


def merge_models(
    scraper_models: List[ModelInfo],
    api_models: List[ModelInfo],
) -> List[ModelInfo]:
    """
    合并爬虫和 API 数据。
    爬虫为主：name, vendor, category, tags
    API 为主：created_at, api_owned_by, max_tokens, context_window
    """
    api_index = build_api_index(api_models)

    merged = []
    for model in scraper_models:
        api = api_index.get(model.id)
        if api:
            # 合并 scraped 字段
            if api.scraped:
                if model.scraped:
                    model.scraped.created_at = model.scraped.created_at or api.scraped.created_at
                    model.scraped.api_owned_by = model.scraped.api_owned_by or api.scraped.api_owned_by
                else:
                    model.scraped = api.scraped
            if not model.description and api.description:
                model.description = api.description
        merged.append(model)

    # 追加 API 中有但爬虫中没有的模型
    scraper_ids = {m.id for m in scraper_models}
    for api_model in api_models:
        if api_model.id not in scraper_ids:
            api_model.rank = len(merged) + 1
            merged.append(api_model)

    return merged
