"""
NVIDIA 页面爬虫
爬取 build.nvidia.com 上的热门模型列表
按页面热度排序
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
        """爬取模型列表（页面热度排序 + API 补全）"""
        print(f"🔍 NVIDIA: 开始获取热门模型 (目标: {limit} 个)")

        try:
            await self._init_browser()

            await self.page.goto(
                "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC",
                wait_until="networkidle"
            )
            await self.page.wait_for_timeout(3000)

            page_models = await self._extract_models_from_page()
            print(f"📄 从页面获取到 {len(page_models)} 个模型（按热度排序）")

            api_model_map = await self._fetch_api_model_map()
            print(f"📡 API 可用模型: {len(api_model_map)} 个")

            result = []
            for i, pm in enumerate(page_models, 1):
                api_id = self._convert_to_api_id(pm.id, pm.href, api_model_map)
                
                model = ModelInfo(
                    id=api_id,
                    name=pm.name,
                    vendor=api_id.split("/")[0] if "/" in api_id else pm.vendor,
                    rank=i,
                    is_downloadable=pm.is_downloadable,
                    is_free_endpoint=pm.is_free_endpoint,
                    tags=pm.tags
                )
                result.append(model)
                print(f"\r[{i}/{len(page_models)}] #{i} {api_id}", end="", flush=True)

            if len(result) < limit and api_model_map:
                existing_ids = {m.id for m in result}
                api_list = await self._fetch_api_model_list()
                for am in api_list:
                    if am.id not in existing_ids and len(result) < limit:
                        am.rank = len(result) + 1
                        result.append(am)
                
                if len(result) > len(page_models):
                    print(f"\n📡 从 API 补充了 {len(result) - len(page_models)} 个模型")

            await self.close()

            final = result[:limit]
            print(f"\n✅ 共获取 {len(final)} 个模型")
            return final

        except Exception as e:
            print(f"\n❌ 爬虫失败: {e}")
            try:
                await self.close()
            except Exception:
                pass
            
            print("⚠️ 回退到 API 列表...")
            return await self._fetch_api_model_list()[:limit]

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

    def _convert_to_api_id(self, page_name: str, href: str, api_map: Dict[str, str]) -> str:
        """把页面上的模型名转成 API ID
        
        页面格式: href="/moonshotai/kimi-k2.5", name="kimi-k2.5"
        API 格式: "moonshotai/kimi-k2.5"
        """
        if href and href.startswith("/"):
            parts = href.strip("/").split("/")
            if len(parts) >= 2:
                candidate = f"{parts[0]}/{parts[1]}"
                if candidate in api_map.values() or candidate in api_map:
                    return candidate
                
                for api_id in api_map.values():
                    if parts[-1].lower() in api_id.lower():
                        return api_id

        if page_name in api_map:
            return api_map[page_name]

        for key, api_id in api_map.items():
            if page_name.lower().replace("-", "").replace("_", "") == key.lower().replace("-", "").replace("_", ""):
                return api_id
            if page_name.lower() in key.lower() or key.lower() in page_name.lower():
                return api_id

        if href and href.startswith("/"):
            parts = href.strip("/").split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"

        return page_name

    async def _fetch_api_model_list(self) -> List[ModelInfo]:
        """从 NVIDIA API 获取完整模型列表"""
        api_url = "https://integrate.api.nvidia.com/v1/models"
        api_key = os.getenv("NVIDIA_API_KEY")

        models = []

        if not api_key:
            return models

        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(api_url, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("data", []):
                        full_id = m.get("id", "")
                        if full_id:
                            vendor = full_id.split("/")[0] if "/" in full_id else "unknown"
                            model = ModelInfo(
                                id=full_id,
                                name=full_id,
                                vendor=vendor,
                                is_free_endpoint=True,
                                tags=[]
                            )
                            models.append(model)

        except Exception as e:
            print(f"⚠️ API 请求失败: {e}")

        return models

    async def _fetch_api_model_map(self) -> Dict[str, str]:
        """从 NVIDIA API 获取模型 ID 映射表"""
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
                            model_map[full_id] = full_id

        except Exception:
            pass

        return model_map

    async def _extract_models_from_page(self) -> List[ModelInfo]:
        """从页面提取模型数据（使用正确的选择器）"""
        models = []

        try:
            headings = await self.page.query_selector_all('h3 a[href]')
            
            print(f"\n📋 页面选择器 'h3 a[href]' 找到 {len(headings)} 个元素", flush=True)
            
            for i, link in enumerate(headings, 1):
                try:
                    model_name = (await link.text_content() or "").strip()
                    href = (await link.get_attribute('href') or "")

                    if not model_name or len(model_name) < 2:
                        continue

                    vendor = "unknown"
                    if href and href.startswith("/"):
                        parts = href.strip("/").split("/")
                        if len(parts) >= 2:
                            vendor = parts[0]

                    temp_model = ModelInfo(
                        id=model_name,
                        name=model_name,
                        vendor=vendor,
                        rank=i,
                        is_downloadable=False,
                        is_free_endpoint=True,
                        tags=[],
                        href=href
                    )
                    models.append(temp_model)
                    
                    if i <= 5 or i == len(headings):
                        print(f"  #{i}: {model_name} ({vendor})", flush=True)

                except Exception as e:
                    print(f"  ⚠️ #{i} 提取失败: {type(e).__name__}", flush=True)
                    continue

        except Exception as e:
            print(f"⚠️ 页面提取失败: {e}", flush=True)

        return models