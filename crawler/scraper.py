"""
NVIDIA 模型爬虫
使用 Playwright 抓取 build.nvidia.com 页面，获取按热度排序的模型列表
"""

import asyncio
import json
import os
import httpx
from typing import List, Optional, Dict
from playwright.async_api import async_playwright

from .models import ModelInfo


class NvidiaScraper:
    """NVIDIA 模型爬虫"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None

    async def init_browser(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--ignore-certificate-errors", "--ignore-certificate-errors-spki-list"]
        )
        self.page = await self.browser.new_page()

        # 设置超时
        self.page.set_default_timeout(60000)

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()

    async def scrape_models(self, url: str = "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC",
                          limit: int = 50) -> List[ModelInfo]:
        """爬取模型列表（支持分页）"""
        print(f"🚀 开始爬取: {url} (目标: {limit} 个模型)")

        if not self.page:
            await self.init_browser()

        try:
            # 访问页面
            await self.page.goto(url, wait_until="networkidle")

            # 等待页面加载完成
            await self.page.wait_for_timeout(5000)

            all_models = []
            page_count = 0

            # 一次性获取 API 模型映射表（避免重复请求）
            api_model_map = await self._fetch_api_model_map()

            # 分页爬取，直到达到目标数量
            while len(all_models) < limit:
                page_count += 1
                print(f"📄 爬取第 {page_count} 页...")

                # 尝试多种方式获取模型数据
                models = await self._extract_models()

                if not models:
                    print("⚠️  无法获取模型数据，尝试备用方案...")
                    models = await self._fallback_extract()

                if not models:
                    print("❌ 页面没有更多模型数据")
                    break

                # 去重（基于当前 all_models 的 ID 集合）
                existing_ids = {m.id for m in all_models}
                new_models = [m for m in models if m.id not in existing_ids]

                # ⚡ 动态映射：通过 NVIDIA API 获取完整ID列表
                # 这一步会把短名称（如 "kimi-k2.5"）转换成完整ID（如 "moonshotai/kimi-k2.5"）
                standardized_models = []
                api_model_map = await self._fetch_api_model_map()

                for model in new_models:
                    full_id = self._find_matching_model_id(model.id, api_model_map)
                    model.id = full_id
                    model.name = full_id
                    model.vendor = full_id.split("/")[0] if "/" in full_id else "unknown"
                    standardized_models.append(model)

                # 再次去重：标准化后的 ID 可能重复（同一模型在不同页面出现）
                seen_ids = {m.id for m in all_models}
                final_models = []
                for m in standardized_models:
                    if m.id not in seen_ids:
                        final_models.append(m)
                        seen_ids.add(m.id)

                all_models.extend(final_models)
                print(f"📊 当前总计: {len(all_models)} 个模型")

                # 尝试滚动加载更多
                if len(all_models) < limit:
                    scroll_success = await self._scroll_for_more()
                    if not scroll_success:
                        print("⚠️  无法加载更多模型")
                        break

            # 限制返回数量
            final_models = all_models[:limit]
            print(f"✅ 成功获取 {len(final_models)} 个模型（去重后）")
            return final_models

        except Exception as e:
            print(f"❌ 爬取失败: {e}")
            return []

    async def _extract_models(self) -> List[ModelInfo]:
        """提取模型数据（包含标签）"""
        models = []

        try:
            # 方法1: 从卡片元素提取
            model_cards = await self.page.query_selector_all(
                "div[class*='model'], div[class*='card'], article[class*='model'], [data-testid*='model']"
            )

            print(f"🔍 找到 {len(model_cards)} 个模型卡片")

            for i, card in enumerate(model_cards[:50], 1):
                try:
                    # 获取模型ID (short name)
                    model_name_elem = await card.query_selector(
                        "h1, h2, h3, h4, h5, [class*='model-title'], [class*='modelName'], [class*='name']"
                    )
                    model_name = await model_name_elem.text_content() if model_name_elem else f"unknown-{i}"
                    model_name = model_name.strip()

                    # 提取标签（Downloadable, Free endpoint等）
                    tags = []
                    downloadable = False
                    free_endpoint = True  # 默认免费

                    # 查找标签元素
                    tag_elements = await card.query_selector_all(
                        "[class*='badge'], [class*='tag'], [class*='pill'], span[class*='badge']"
                    )

                    for tag_elem in tag_elements:
                        tag_text = await tag_elem.text_content()
                        tag_text = tag_text.strip().lower()

                        if 'downloadable' in tag_text or 'download' in tag_text:
                            downloadable = True
                            tags.append('downloadable')
                        elif 'free' in tag_text:
                            tags.append('free')
                        elif 'paid' in tag_text or 'enterprise' in tag_text:
                            free_endpoint = False
                            tags.append('paid')

                    # 检查是否有下载按钮/链接
                    download_link = await card.query_selector(
                        "a[href*='download'], button[class*='download'], [class*='download']"
                    )
                    if download_link and not downloadable:
                        downloadable = True
                        tags.append('downloadable')

                    # 获取供应商（从模型名中提取）
                    vendor = "unknown"
                    if "/" in model_name:
                        vendor = model_name.split("/")[0]
                    else:
                        # 尝试从卡片中找供应商
                        vendor_elem = await card.query_selector(
                            "[class*='vendor'], [class*='organization']"
                        )
                        if vendor_elem:
                            vendor_text = await vendor_elem.text_content()
                            vendor = vendor_text.strip().lower().replace(" ", "-")

                    model = ModelInfo(
                        id=model_name,
                        name=model_name,
                        vendor=vendor,
                        rank=i,
                        is_available=True,
                        test_status="pending",
                        is_downloadable=downloadable,
                        is_free_endpoint=free_endpoint,
                        tags=tags
                    )
                    models.append(model)

                    # 打印标签信息（调试）
                    if tags:
                        print(f"  Model #{i}: {model_name} - Tags: {tags}")

                except Exception as e:
                    print(f"⚠️  解析卡片 {i} 失败: {e}")
                    continue

        except Exception as e:
            print(f"⚠️  提取模型失败: {e}")

        return models

    async def _fetch_api_model_map(self) -> Dict[str, str]:
        """
        从 NVIDIA API 获取完整模型列表，建立短名→完整ID的映射

        Returns:
            Dict[short_name, full_id] 例如: {"kimi-k2.5": "moonshotai/kimi-k2.5"}
        """
        import httpx
        import os

        api_url = "https://integrate.api.nvidia.com/v1/models"
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("请设置 NVIDIA_API_KEY 环境变量以获取模型映射")

        model_map = {}

        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(api_url, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])

                    for m in models:
                        full_id = m.get("id", "")
                        if full_id:
                            # 提取短名：从 "vendor/model-name" 中取 "model-name"
                            short_name = full_id.split("/")[-1] if "/" in full_id else full_id
                            model_map[short_name] = full_id

                    print(f"🌐 API 映射表: {len(model_map)} 个模型")
                else:
                    print(f"⚠️  API 获取失败: {resp.status_code}")
        except Exception as e:
            print(f"⚠️  API 请求异常: {e}")

        return model_map

    def _find_matching_model_id(self, short_name: str, api_map: Dict[str, str]) -> str:
        """
        从 API 映射表中找到匹配的完整ID

        Args:
            short_name: 短名称（如 "kimi-k2.5"）
            api_map: 短名→完整ID 的映射表

        Returns:
            完整ID，如果找不到则返回原短名
        """
        # 精确匹配
        if short_name in api_map:
            return api_map[short_name]

        # 模糊匹配：查找包含短名的模型
        for key, full_id in api_map.items():
            if short_name.lower() in key.lower() or key.lower() in short_name.lower():
                return full_id

        # 都没匹配到，返回原名称（后续测试可能会失败）
        return short_name

    async def _fallback_extract(self) -> List[ModelInfo]:
        """备用提取方法"""
        models = []

        # 尝试获取页面文本并解析
        try:
            page_text = await self.page.evaluate("document.body.innerText")

            # 从文本中提取可能的模型ID
            import re
            model_patterns = [
                r'[a-z0-9_-]+/[a-z0-9_-]+',  # vendor/model 格式
                r'model-[a-z0-9-]+',         # model-xxx 格式
                r'[A-Z][a-z]+\s+\d+[A-Z]*',    # 如 Gemini 2B
            ]

            for pattern in model_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for i, match in enumerate(matches[:50], 1):
                    if len(match) > 3:  # 过滤掉太短的匹配
                        vendor = match.split("/")[0] if "/" in match else "unknown"
                        model = ModelInfo(
                            id=match,
                            name=match,
                            vendor=vendor,
                            rank=i,
                            is_available=True,
                            test_status="pending"
                        )
                        models.append(model)

        except Exception as e:
            print(f"⚠️  备用方法失败: {e}")

        # 如果还是没找到，使用已知的热门模型
        if not models:
            known_models = [
                "qwen/qwen3-coder-480b-a35b-instruct",
                "google/gemma-4-31b-it",
                "meta/llama-4-maverick-17b-128e-instruct",
                "deepseek-ai/deepseek-v3.1-terminus",
                "minimaxai/minimax-m2.7",
                "moonshotai/kimi-k2-instruct-0905",
                "z-ai/glm4.7",
                "stepfun-ai/step-3.5-flash",
                "qwen/qwen3.5-122b-a10b",
                "google/gemma-7b",
                "microsoft/phi-3-mini-128k-instruct",
            ]

            for i, model_id in enumerate(known_models[:50], 1):
                vendor = model_id.split("/")[0]
                model = ModelInfo(
                    id=model_id,
                    name=model_id,
                    vendor=vendor,
                    rank=i,
                    is_available=True,
                    test_status="pending"
                )
                models.append(model)

        return models

    async def _scroll_for_more(self) -> bool:
        """滚动页面以加载更多模型"""
        try:
            # 滚动到页面底部
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # 等待加载
            await self.page.wait_for_timeout(2000)

            # 检查是否有加载指示器
            loading_selectors = [
                "[class*='loading']",
                "[class*='spinner']",
                "[class*='progress']",
                "[data-testid*='loading']"
            ]

            for selector in loading_selectors:
                if await self.page.query_selector(selector):
                    # 等待加载完成
                    await self.page.wait_for_timeout(3000)
                    return True

            return False

        except Exception as e:
            print(f"⚠️  滚动失败: {e}")
            return False

    async def _get_model_details(self, model_short_name: str) -> dict:
        """获取模型详情（包括完整ID和调用代码）"""
        try:
            # 访问模型详情页面
            detail_url = f"https://build.nvidia.com/{model_short_name}"
            await self.page.goto(detail_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            # 点击 "View Code" 按钮
            view_code_button = await self.page.query_selector(
                "button[class*='view-code'], button:has-text('View Code'), [data-testid*='view-code']"
            )

            if view_code_button:
                await view_code_button.click()
                await self.page.wait_for_timeout(2000)

                # 等待弹窗出现
                modal_overlay = await self.page.query_selector(".nv-modal-overlay, [class*='modal']")
                if modal_overlay:
                    # 提取调用代码
                    code_element = await self.page.query_selector("code, pre")
                    if code_element:
                        code_content = await code_element.text_content()

                        # 从代码中提取完整模型ID
                        import re
                        model_id_match = re.search(r'model[\s:]*["\']([^"\']+)["\']', code_content or "")
                        full_model_id = model_id_match.group(1) if model_id_match else model_short_name

                        return {
                            "id": full_model_id,
                            "code": code_content,
                            "url": detail_url
                        }

            # 如果无法获取详情，返回基本信息
            return {"id": model_short_name, "code": None, "url": detail_url}

        except Exception as e:
            print(f"⚠️  获取模型详情失败 {model_short_name}: {e}")
            return {"id": model_short_name, "code": None, "url": f"https://build.nvidia.com/{model_short_name}"}


async def scrape_top_models(limit: int = 50, sort_by: str = "popular") -> List[ModelInfo]:
    """爬取前N个热门模型

    Args:
        limit: 爬取的模型数量
        sort_by: 排序方式，'popular' 或 'recent'
    """
    scraper = NvidiaScraper(headless=True)
    try:
        # 根据排序方式构建 URL
        if sort_by == "popular":
            url = "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC"
        else:  # recent
            url = "https://build.nvidia.com/models"

        models = await scraper.scrape_models(limit=limit, url=url)
        return models
    finally:
        await scraper.close()


if __name__ == "__main__":
    # 测试爬虫
    async def test():
        models = await scrape_top_models(20)
        for m in models:
            print(f"#{m.rank:2d} {m.id}")

    asyncio.run(test())