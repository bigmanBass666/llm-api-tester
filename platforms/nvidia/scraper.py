"""
NVIDIA 页面爬虫
爬取 build.nvidia.com 上的热门模型列表
"""

import asyncio
import httpx
import re
from typing import List, Dict
from playwright.async_api import async_playwright

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ModelInfo
from platforms.base.base_scraper import BaseScraper


class NvidiaScraper(BaseScraper):
    """NVIDIA 模型爬虫"""

    platform_name = "nvidia"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None

    async def scrape(self, limit: int = 50) -> List[ModelInfo]:
        """爬取模型列表"""
        print(f"🔍 NVIDIA: 开始爬取热门模型 (目标: {limit} 个)")

        await self._init_browser()

        try:
            await self.page.goto(
                "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC",
                wait_until="networkidle"
            )
            await self.page.wait_for_timeout(3000)

            api_model_map = await self._fetch_api_model_map()

            all_models = []
            page_count = 0

            while len(all_models) < limit:
                page_count += 1
                print(f"\r📄 NVIDIA: 正在爬取第 {page_count} 页... (已获取 {len(all_models)}/{limit})", end="")

                models = await self._extract_models()

                if not models:
                    break

                existing_ids = {m.id for m in all_models}
                new_models = [m for m in models if m.id not in existing_ids]

                standardized_models = []
                for model in new_models:
                    full_id = self._find_matching_model_id(model.id, api_model_map)
                    model.id = full_id
                    model.name = full_id
                    model.vendor = full_id.split("/")[0] if "/" in full_id else "unknown"
                    standardized_models.append(model)

                seen_ids = {m.id for m in all_models}
                for m in standardized_models:
                    if m.id not in seen_ids:
                        all_models.append(m)
                        seen_ids.add(m.id)

                if len(all_models) < limit:
                    scroll_success = await self._scroll_for_more()
                    if not scroll_success:
                        break

            print(f"\n✅ NVIDIA: 爬取完成，共 {len(all_models)} 个模型")
            return all_models[:limit]

        except Exception as e:
            print(f"\n❌ NVIDIA: 爬取失败 - {e}")
            return []

        finally:
            await self.close()

    async def _init_browser(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--ignore-certificate-errors"]
        )
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(60000)

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()

    async def _fetch_api_model_map(self) -> Dict[str, str]:
        """从 NVIDIA API 获取完整模型列表"""
        import os
        api_url = "https://integrate.api.nvidia.com/v1/models"
        api_key = os.getenv("NVIDIA_API_KEY")

        model_map = {}

        if not api_key:
            return model_map

        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(api_url, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("data", []):
                        full_id = m.get("id", "")
                        if full_id:
                            short_name = full_id.split("/")[-1] if "/" in full_id else full_id
                            model_map[short_name] = full_id

        except Exception:
            pass

        return model_map

    def _find_matching_model_id(self, short_name: str, api_map: Dict[str, str]) -> str:
        """从 API 映射表中找到匹配的完整ID"""
        if short_name in api_map:
            return api_map[short_name]

        for key, full_id in api_map.items():
            if short_name.lower() in key.lower() or key.lower() in short_name.lower():
                return full_id

        return short_name

    async def _extract_models(self) -> List[ModelInfo]:
        """提取模型数据"""
        models = []

        try:
            model_cards = await self.page.query_selector_all(
                "div[class*='model'], div[class*='card'], article[class*='model']"
            )

            for i, card in enumerate(model_cards, 1):
                try:
                    model_name_elem = await card.query_selector(
                        "h1, h2, h3, h4, h5, [class*='model-title'], [class*='modelName']"
                    )
                    model_name = await model_name_elem.text_content() if model_name_elem else f"unknown-{i}"
                    model_name = model_name.strip()

                    tags = []
                    downloadable = False
                    free_endpoint = True

                    tag_elements = await card.query_selector_all(
                        "[class*='badge'], [class*='tag'], span[class*='badge']"
                    )

                    for tag_elem in tag_elements:
                        tag_text = (await tag_elem.text_content() or "").strip().lower()
                        if 'downloadable' in tag_text or 'download' in tag_text:
                            downloadable = True
                            tags.append('downloadable')
                        elif 'free' in tag_text:
                            tags.append('free')

                    vendor = model_name.split("/")[0] if "/" in model_name else "unknown"

                    model = ModelInfo(
                        id=model_name,
                        name=model_name,
                        vendor=vendor,
                        rank=i,
                        is_downloadable=downloadable,
                        is_free_endpoint=free_endpoint,
                        tags=tags
                    )
                    models.append(model)

                except Exception:
                    continue

        except Exception:
            pass

        return models

    async def _scroll_for_more(self) -> bool:
        """滚动页面以加载更多模型"""
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(2000)
            return True
        except Exception:
            return False