"""
NVIDIA 模型爬虫 - 兼容层（Compatibility Layer）

⚠️ 重要提示：
这是旧版爬虫的兼容层，内部实现已委托给新版 platforms.nvidia.scraper。
建议新项目直接使用新导入路径：
    from platforms.nvidia.scraper import NvidiaScraper, scrape_top_models

保留此模块仅为向后兼容，支持现有代码的导入路径：
    from crawler.scraper import NvidiaScraper, scrape_top_models, fix_model_id
"""

import asyncio
from typing import List

# 导入新版实现（使用下划线前缀避免命名冲突）
from platforms.nvidia.scraper import NvidiaScraper as _NvidiaScraper
from platforms.nvidia.scraper import scrape_top_models as _scrape_top_models

# 导入 ModelInfo（从 src.models 统一导入）
from src.models import ModelInfo


def fix_model_id(model_id: str) -> str:
    """将 NVIDIA 网页 ID 转换为 API 所需的 ID 格式

    NVIDIA 网页 URL 使用下划线 (deepseek-v3_2)，
    但实际 API 需要点号 (deepseek-v3.2)

    Args:
        model_id: 从网页提取的原始 ID

    Returns:
        修复后的 ID（下划线替换为点号）
    """
    return model_id.replace('_', '.')


class NvidiaScraper(_NvidiaScraper):
    """NVIDIA 模型爬虫 - 兼容层包装器

    继承自 platforms.nvidia.scraper.NvidiaScraper，提供向后兼容的 API。

    兼容的接口：
    - scrape_models(url, limit, page_size): 旧版方法，内部调用新版 scrape()
    - init_browser(): 初始化浏览器
    - close(): 关闭浏览器

    建议迁移到：
        from platforms.nvidia.scraper import NvidiaScraper
        scraper = NvidiaScraper()
        models = await scraper.scrape(limit=50, sort_by="popular")
    """

    async def scrape_models(self, url: str = None, limit: int = 50, page_size: int = None) -> List[ModelInfo]:
        """爬取模型列表（向后兼容的方法）

        此方法为兼容旧版代码而保留，内部调用新版的 scrape() 方法。

        Args:
            url: 页面URL（已废弃，保留参数仅用于兼容，实际使用 sort_by 逻辑）
            limit: 目标模型数量
            page_size: 每页显示数量（已废弃，保留参数仅用于兼容）

        Returns:
            ModelInfo 列表
        """
        # 从 URL 推断排序方式（向后兼容）
        sort_by = "popular"  # 默认热度排序
        if url and "orderBy" in url and "recent" in url.lower():
            # URL 包含 recent 相关参数，使用最新排序
            sort_by = "recent"

        # 调用新版实现
        return await self.scrape(limit=limit, sort_by=sort_by)

    async def init_browser(self):
        """初始化浏览器（向后兼容的方法）

        新版实现中浏览器在 scrape() 方法内部自动初始化，
        此方法保留仅用于兼容旧代码。
        """
        # 新版实现中浏览器初始化在 _init_browser 中
        # 如果需要在 scrape 之前手动初始化，调用内部方法
        if not self.browser:
            await self._init_browser()


async def scrape_top_models(limit: int = 50, sort_by: str = "platforms", filter_text_models: bool = False, model_type_filter=None, usecase_filter=None) -> List[ModelInfo]:
    """爬取前N个热门模型（向后兼容的便捷函数）

    此函数直接委托给 platforms.nvidia.scraper.scrape_top_models

    Args:
        limit: 爬取的模型数量
        sort_by: 排序方式，'popular' 或 'recent'
        filter_text_models: (已废弃) 是否只爬取文字模型，建议使用 model_type_filter
        model_type_filter: 模型类型过滤（None=全部, ModelType.TEXT=仅文本, ModelType.IMAGE_GENERATION=仅文生图）
        usecase_filter: 用例过滤，如 'text-generation', 'image-generation' 等

    Returns:
        ModelInfo 列表

    建议迁移到：
        from platforms.nvidia.scraper import scrape_top_models
        models = await scrape_top_models(limit=50, sort_by="popular")
    """
    from src.models import ModelType
    if model_type_filter is None and filter_text_models:
        model_type_filter = ModelType.TEXT
    return await _scrape_top_models(limit=limit, sort_by=sort_by, model_type_filter=model_type_filter, usecase_filter=usecase_filter)


# 向后兼容：从配置加载器获取配置常量
from src.platform_config import PlatformConfigLoader

TEXT_MODEL_CATEGORIES = PlatformConfigLoader.get_text_model_categories("nvidia")
NON_TEXT_KEYWORDS = PlatformConfigLoader.get_non_text_keywords("nvidia")


if __name__ == "__main__":
    # 测试兼容层
    async def test():
        print("🧪 测试兼容层...")

        # 测试 fix_model_id
        assert fix_model_id("deepseek-v3_2") == "deepseek-v3.2"
        print("✅ fix_model_id 工作正常")

        # 测试 scrape_top_models
        models = await scrape_top_models(5)
        print(f"✅ scrape_top_models 返回 {len(models)} 个模型")
        for m in models:
            print(f"  #{m.rank:2d} {m.id}")

        # 测试 NvidiaScraper 类
        scraper = NvidiaScraper()
        print(f"✅ NvidiaScraper 实例化成功 (headless={scraper.headless})")
        await scraper.close()

    asyncio.run(test())
