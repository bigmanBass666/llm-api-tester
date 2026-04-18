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
        """爬取模型列表（优先使用 API）"""
        print(f"🔍 NVIDIA: 开始获取热门模型 (目标: {limit} 个)")

        api_models = await self._fetch_api_model_list()

        if len(api_models) >= limit:
            print(f"✅ 从 API 获取到 {len(api_models)} 个模型")
            return api_models[:limit]

        print(f"⚠️ API 仅返回 {len(api_models)} 个，尝试补充页面数据...")

        try:
            await self._init_browser()

            await self.page.goto(
                "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC",
                wait_until="networkidle"
            )
            await self.page.wait_for_timeout(3000)

            page_models = await self._extract_models_from_page()
            await self.close()

            merged = {m.id: m for m in api_models}
            for pm in page_models:
                if pm.id not in merged:
                    merged[pm.id] = pm

            result = list(merged.values())[:limit]
            print(f"✅ 合并后共 {len(result)} 个模型")
            return result

        except Exception as e:
            print(f"⚠️ 页面爬取失败，使用 API 数据: {e}")
            return api_models[:limit]

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

    async def _fetch_api_model_list(self) -> List[ModelInfo]:
        """从 NVIDIA API 获取完整模型列表"""
        import os
        api_url = "https://integrate.api.nvidia.com/v1/models"
        api_key = os.getenv("NVIDIA_API_KEY")

        models = []

        if not api_key:
            print("⚠️ 未设置 NVIDIA_API_KEY")
            return models

        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(api_url, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    for i, m in enumerate(data.get("data", []), 1):
                        full_id = m.get("id", "")
                        if full_id:
                            vendor = full_id.split("/")[0] if "/" in full_id else "unknown"
                            model = ModelInfo(
                                id=full_id,
                                name=full_id,
                                vendor=vendor,
                                rank=i,
                                is_free_endpoint=True,
                                tags=[]
                            )
                            models.append(model)

        except Exception as e:
            print(f"⚠️ API 请求失败: {e}")

        return models

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

    async def _extract_models_from_page(self) -> List[ModelInfo]:
        """从页面提取模型数据"""
        models = []

        try:
            model_cards = await self.page.query_selector_all(
                'a[href*="/models/"], div[class*="model-card"]'
            )

            if not model_cards:
                model_cards = await self.page.query_selector_all(
                    'h3 a[href*="/"]'
                )

            for i, card in enumerate(model_cards[:50], 1):
                try:
                    heading = await card.query_selector('h3, h2')
                    model_name = (await heading.text_content() or "").strip() if heading else ""

                    if not model_name:
                        link = await card.query_selector('a[href]')
                        if link:
                            href = (await link.get_attribute('href') or "")
                            model_name = href.rstrip('/').split('/')[-1]

                    if not model_name or len(model_name) < 2:
                        continue

                    tags = []
                    downloadable = False
                    free_endpoint = True

                    tag_elements = await card.query_selector_all(
                        '[class*="badge"], [class*="tag"], span[class*="label"]'
                    )
                    for tag_elem in tag_elements:
                        tag_text = (await tag_elem.text_content() or "").strip().lower()
                        if 'downloadable' in tag_text or 'download' in tag_text:
                            downloadable = True
                            tags.append('downloadable')
                        elif 'free' in tag_text:
                            tags.append('free')

                    dl_element = await card.query_selector('[class*="downloadable"]')
                    if dl_element and not downloadable:
                        downloadable = True
                        tags.append('downloadable')

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

        except Exception as e:
            print(f"⚠️ 页面提取失败: {e}")

        return models

    async def _scroll_for_more(self) -> bool:
        """滚动页面以加载更多模型"""
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(2000)
            return True
        except Exception:
            return False