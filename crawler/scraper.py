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
from .logger import get_logger

logger = get_logger(__name__)


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
            max_scroll_attempts = 20
            consecutive_no_new = 0
            max_consecutive_no_new = 3

            # 一次性获取 API 模型映射表（避免重复请求）
            api_model_map = await self._fetch_api_model_map()

            # 分页爬取，直到达到目标数量或达到最大尝试次数
            while len(all_models) < limit and page_count < max_scroll_attempts:
                page_count += 1
                logger.debug(f"爬取第 {page_count} 页 (当前: {len(all_models)}/{limit})")

                # 记录滚动前的模型数量
                models_before_scroll = len(all_models)

                # 尝试多种方式获取模型数据
                models = await self._extract_models()

                if not models:
                    logger.warning("无法获取模型数据，尝试备用方案")
                    models = await self._fallback_extract()

                if not models:
                    logger.debug("页面没有更多模型数据")
                    break

                # 去重（基于当前 all_models 的 ID 集合）
                existing_ids = {m.id for m in all_models}
                new_models = [m for m in models if m.id not in existing_ids]

                # ⚡ 动态映射：通过 NVIDIA API 获取完整ID列表
                # 这一步会把短名称（如 "kimi-k2.5"）转换成完整ID（如 "moonshotai/kimi-k2.5"）
                standardized_models = []

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

                # 检测是否有新模型加载
                new_models_count = len(final_models)
                print(f"📊 本页新增: {new_models_count} 个模型 | 总计: {len(all_models)} 个模型")

                if new_models_count == 0:
                    consecutive_no_new += 1
                    logger.warning(f"连续 {consecutive_no_new} 次无新模型")
                    if consecutive_no_new >= max_consecutive_no_new:
                        logger.info("达到最大连续无新内容次数，停止爬取")
                        break
                else:
                    consecutive_no_new = 0  # 重置计数器

                # 尝试滚动加载更多
                if len(all_models) < limit:
                    scroll_success = await self._scroll_for_more()
                    if not scroll_success:
                        logger.warning(f"滚动未检测到新内容 (尝试 {page_count}/{max_scroll_attempts})")

            # 限制返回数量
            final_models = all_models[:limit]
            print(f"✅ 成功获取 {len(final_models)} 个模型（去重后）")
            return final_models

        except Exception as e:
            logger.error(f"爬取失败: {e}")
            return []

    async def _extract_models(self) -> List[ModelInfo]:
        """提取模型数据（包含标签）"""
        models = []

        try:
            # 方法1: 从卡片元素提取
            model_cards = await self.page.query_selector_all(
                "div[class*='model'], div[class*='card'], article[class*='model'], [data-testid*='model']"
            )

            logger.debug(f"找到 {len(model_cards)} 个模型卡片")

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
                        logger.debug(f"Model #{i}: {model_name} - Tags: {tags}")

                except Exception as e:
                    logger.warning(f"解析卡片 {i} 失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"提取模型失败: {e}")

        return models

    async def _fetch_api_model_map(self) -> Dict[str, str]:
        """
        从 NVIDIA API 获取完整模型列表，建立短名→完整ID的映射
        包含增强的 SSL 配置、详细错误处理和自动重试机制

        Returns:
            Dict[short_name, full_id] 例如: {"kimi-k2.5": "moonshotai/kimi-k2.5"}
        """
        import httpx
        import os
        import ssl
        import asyncio

        api_url = "https://integrate.api.nvidia.com/v1/models"
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("请设置 NVIDIA_API_KEY 环境变量以获取模型映射")

        model_map = {}
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"正在获取 API 映射表 (第 {attempt}/{max_retries} 次)...")

                # 创建自定义 SSL context（完全禁用证书验证）
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(45.0, connect=15.0),
                    verify=ssl_context,
                    trust_env=True  # 使用环境变量中的代理和证书设置
                ) as client:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    resp = await client.get(api_url, headers=headers)

                    if resp.status_code == 200:
                        data = resp.json()
                        models = data.get("data", [])

                        for m in models:
                            full_id = m.get("id", "")
                            if full_id:
                                short_name = full_id.split("/")[-1] if "/" in full_id else full_id
                                model_map[short_name] = full_id

                        logger.info(f"✅ API 映射表: {len(model_map)} 个模型")
                        return model_map  # 成功，直接返回
                    else:
                        logger.warning(f"API 返回错误: HTTP {resp.status_code}")
                        if attempt < max_retries:
                            await asyncio.sleep(retry_delay)
                            continue

            except httpx.ConnectError as e:
                logger.warning(f"连接失败 (尝试 {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
            except httpx.TimeoutException as e:
                logger.warning(f"请求超时 (尝试 {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP 错误 (尝试 {attempt}/{max_retries}): {e.response.status_code}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
            except Exception as e:
                error_type = type(e).__name__
                logger.error(f"API 请求异常 ({error_type}) (尝试 {attempt}/{max_retries}): {e}")

                # 打印详细堆栈跟踪（仅在最后一次失败时）
                if attempt == max_retries:
                    import traceback
                    logger.error("API 请求最终失败，详细错误堆栈:")
                    logger.error(traceback.format_exc())

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue

        logger.error(f"经过 {max_retries} 次尝试后仍无法获取 API 映射表")
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
            logger.warning(f"备用方法失败: {e}")

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
        """滚动页面以加载更多模型（增强版）

        Returns:
            bool: 是否成功触发加载（不依赖loading indicator）
        """
        try:
            scroll_height_before = await self.page.evaluate("document.body.scrollHeight")

            # 策略：多次小幅度滚动 + 等待（而非一次性滚到底部）
            for scroll_step in range(3):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                await self.page.wait_for_timeout(1500)

            # 额外等待，确保动态内容加载
            await self.page.wait_for_timeout(2000)

            scroll_height_after = await self.page.evaluate("document.body.scrollHeight")

            # 检测是否有新内容（scrollHeight变化说明加载了新内容）
            has_new_content = scroll_height_after > scroll_height_before

            if has_new_content:
                logger.debug(f"滚动成功: 页面高度 {scroll_height_before} -> {scroll_height_after}")
                return True
            else:
                logger.debug(f"滚动后无新内容 (高度: {scroll_height_after})")
                return False

        except Exception as e:
            logger.warning(f"滚动失败: {e}")
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
            logger.warning(f"获取模型详情失败 {model_short_name}: {e}")
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