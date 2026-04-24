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

        # 设置超时（增加到180秒以应对更严重的网络延迟）
        self.page.set_default_timeout(180000)

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()

    async def scrape_models(self, url: str = "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC&pageSize=96",
                          limit: int = 50, page_size: int = 96) -> List[ModelInfo]:
        """爬取模型列表（支持分页）

        Args:
            url: 页面URL（已包含pageSize参数）
            limit: 目标模型数量
            page_size: 每页显示数量（默认96，可减少HTTP请求次数）
        """
        print(f"🚀 开始爬取: {url} (目标: {limit} 个模型, 每页: {page_size} 个)")

        if not self.page:
            await self.init_browser()

        try:
            # 确保URL包含pageSize参数（如果未指定则添加）
            if "pageSize" not in url:
                url = f"{url}&pageSize={page_size}" if "?" in url else f"{url}?pageSize={page_size}"
                logger.debug(f"自动添加pageSize参数: {url}")

            # 访问页面（带重试机制，增强网络鲁棒性）
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"正在加载页面 (尝试 {attempt}/{max_retries})...")
                    await self.page.goto(url, wait_until="networkidle", timeout=120000)
                    logger.info("✅ 页面加载成功（networkidle）")
                    break
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"页面加载失败 (尝试 {attempt}/{max_retries}): {e}")
                        # 指数退避等待：3秒、6秒、9秒
                        wait_time = 3 * attempt
                        logger.warning(f"等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)

                        # 最后一次尝试使用 domcontentloaded 作为备选策略
                        if attempt == max_retries - 1:
                            try:
                                logger.warning("networkidle 超时，尝试使用 domcontentloaded 策略")
                                await self.page.goto(url, wait_until="domcontentloaded", timeout=120000)
                                logger.info("✅ 页面加载成功（domcontentloaded）")
                                break
                            except Exception as fallback_e:
                                logger.warning(f"domcontentloaded 策略也失败: {fallback_e}")
                                continue
                    else:
                        logger.error(f"经过 {max_retries} 次尝试后页面仍无法加载")
                        raise e

            # 等待页面加载完成
            await self.page.wait_for_timeout(5000)

            # 关闭可能出现的 Cookie 弹窗（防止阻挡后续操作）
            await self._close_cookie_consent()

            all_models = []
            page_count = 0
            max_page_turns = 10  # 最大翻页次数限制（防止无限循环）
            consecutive_no_new = 0
            max_consecutive_no_new = 3

            # 一次性获取 API 模型映射表（避免重复请求）
            api_model_map = await self._fetch_api_model_map()

            # 分页爬取主循环
            # 使用分页模式而非滚动模式，因为 NVIDIA 网站使用传统分页系统
            # 设置 pageSize=96 后，总页数大幅减少（如192个模型只需2-3页）
            while len(all_models) < limit and page_count < max_page_turns:
                page_count += 1
                logger.info(f"📄 正在爬取第 {page_count} 页 (当前: {len(all_models)}/{limit})")

                # 提取模型数据（带详细诊断）
                models = await self._extract_models()

                if not models:
                    logger.warning("⚠️ 主提取方法返回空列表，尝试备用方案")
                    # 诊断：检查页面状态
                    try:
                        page_title = await self.page.title()
                        card_count = await self.page.query_selector_all("[data-testid='nv-card-root']")
                        body_text = await self.page.evaluate("document.body.innerText")
                        logger.warning(f"  页面标题: {page_title}")
                        logger.warning(f"  nv-card-root 元素数: {len(card_count)}")
                        logger.warning(f"  页面文本长度: {len(body_text)} 字符")
                        logger.warning(f"  页面文本前200字: {body_text[:200]}")
                    except Exception as diag_e:
                        logger.warning(f"  诊断信息获取失败: {diag_e}")

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
                print(f"📊 第{page_count}页新增: {new_models_count} 个模型 | 总计: {len(all_models)} 个模型")

                if new_models_count == 0:
                    consecutive_no_new += 1
                    logger.warning(f"连续 {consecutive_no_new} 次无新模型")
                    if consecutive_no_new >= max_consecutive_no_new:
                        logger.info("达到最大连续无新内容次数，停止爬取")
                        break
                else:
                    consecutive_no_new = 0  # 重置计数器

                # 如果还未达到目标数量，尝试翻到下一页
                if len(all_models) < limit:
                    logger.debug(f"尝试翻到下一页 (已翻 {page_count}/{max_page_turns} 页)")
                    page_success = await self._go_to_next_page()
                    if not page_success:
                        logger.warning(f"翻页失败或已到达末页 (共翻 {page_count} 页)")
                        break

            # 限制返回数量
            final_models = all_models[:limit]
            print(f"✅ 成功获取 {len(final_models)} 个模型（去重后）")
            return final_models

        except Exception as e:
            logger.error(f"爬取失败: {e}")
            return []

    async def _extract_models(self) -> List[ModelInfo]:
        """提取模型数据（使用精确的 data-testid 选择器）

        基于 Playwright 探索发现 NVIDIA 网页使用精确的 data-testid 属性：
        - [data-testid='nv-card-root']: 模型卡片根元素
        - a[data-nvtrack-nav-object-label]: 发布商链接
        - span[data-testid="nv-badge"]: 标签元素
        - a[data-nvtrack-nav-object="artifact-card"]: 模型链接（包含完整ID）
        """
        models = []

        try:
            # Task 4: 使用精确的选择器定位模型卡片
            # 原因：NVIDIA 网站使用 data-testid 属性精确定位组件，比宽泛的 class 选择器更可靠
            model_cards = await self.page.query_selector_all(
                "[data-testid='nv-card-root']"
            )

            logger.debug(f"找到 {len(model_cards)} 个模型卡片 (使用 nv-card-root)")

            for i, card in enumerate(model_cards[:50], 1):
                try:
                    # ===== 初始化默认值 =====
                    model_name = f"unknown-{i}"
                    vendor = "unknown"
                    tags = []
                    downloadable = False
                    free_endpoint = True  # 默认免费
                    full_model_id = None
                    description = None

                    # Task 5.3: 提取完整模型 ID（优先从链接获取）
                    try:
                        card_link = await card.query_selector(
                            "a[data-nvtrack-nav-object='artifact-card']"
                        )
                        if card_link:
                            href = await card_link.get_attribute("href")
                            if href and href.startswith("/"):
                                full_model_id = href.lstrip("/")
                                logger.debug(f"  从链接获取完整ID: {full_model_id}")
                    except Exception as e:
                        logger.debug(f"  提取完整ID失败: {e}")

                    # 获取模型名称（短名称，用于显示）
                    try:
                        model_name_elem = await card.query_selector(
                            "h1, h2, h3, h4, h5, [class*='model-title'], "
                            "[class*='modelName'], [class*='name']"
                        )
                        if model_name_elem:
                            model_name = await model_name_elem.text_content()
                            if model_name:
                                model_name = model_name.strip()

                        # 如果没有获取到名称但获取到了完整ID，使用完整ID的最后一部分
                        if model_name == f"unknown-{i}" and full_model_id:
                            model_name = full_model_id.split("/")[-1] if "/" in full_model_id else full_model_id
                    except Exception as e:
                        logger.debug(f"  提取模型名称失败: {e}")

                    # Task 5.1: 提取发布商信息（vendor）
                    try:
                        vendor_link = await card.query_selector(
                            "a[data-nvtrack-nav-object-label]"
                        )
                        if vendor_link:
                            vendor_text = await vendor_link.text_content()
                            if vendor_text:
                                vendor = vendor_text.strip().lower().replace(" ", "-")
                                logger.debug(f"  发布商: {vendor}")
                        elif full_model_id and "/" in full_model_id:
                            # Fallback: 从完整 ID 中提取发布商
                            vendor = full_model_id.split("/")[0]
                    except Exception as e:
                        logger.debug(f"  提取发布商失败: {e}")
                        # Fallback 到旧逻辑
                        if "/" in model_name:
                            vendor = model_name.split("/")[0]

                    # Task 5.2: 增强标签提取逻辑（使用精确选择器）
                    try:
                        badge_elements = await card.query_selector_all(
                            "span[data-testid='nv-badge']"
                        )

                        if badge_elements:
                            logger.debug(f"  找到 {len(badge_elements)} 个标签")
                            for badge in badge_elements:
                                try:
                                    tag_text = await badge.text_content()
                                    if tag_text:
                                        tag_text = tag_text.strip().lower()
                                        tags.append(tag_text)

                                        # 根据标签内容设置布尔标志
                                        if 'downloadable' in tag_text or 'download' in tag_text:
                                            downloadable = True
                                        elif 'free' in tag_text:
                                            free_endpoint = True
                                        elif 'paid' in tag_text or 'enterprise' in tag_text:
                                            free_endpoint = False
                                except Exception as e:
                                    logger.debug(f"    解析标签失败: {e}")
                                    continue
                        else:
                            # Fallback: 使用旧的宽泛选择器查找标签
                            tag_elements = await card.query_selector_all(
                                "[class*='badge'], [class*='tag'], [class*='pill'], span[class*='badge']"
                            )
                            for tag_elem in tag_elements:
                                try:
                                    tag_text = await tag_elem.text_content()
                                    if tag_text:
                                        tag_text = tag_text.strip().lower()
                                        tags.append(tag_text)
                                        if 'downloadable' in tag_text or 'download' in tag_text:
                                            downloadable = True
                                        elif 'free' in tag_text:
                                            free_endpoint = True
                                        elif 'paid' in tag_text or 'enterprise' in tag_text:
                                            free_endpoint = False
                                except Exception:
                                    continue
                    except Exception as e:
                        logger.debug(f"  提取标签失败: {e}")

                    # 检查下载按钮/链接（补充检测）
                    try:
                        download_link = await card.query_selector(
                            "a[href*='download'], button[class*='download'], [class*='download']"
                        )
                        if download_link and not downloadable:
                            downloadable = True
                            if 'downloadable' not in tags:
                                tags.append('downloadable')
                    except Exception:
                        pass

                    # Task 5.4: 可选 - 提取模型描述文本
                    try:
                        desc_elem = await card.query_selector(
                            "[class*='description'], [class*='desc'], p[class*='summary']"
                        )
                        if desc_elem:
                            desc_text = await desc_elem.text_content()
                            if desc_text:
                                description = desc_text.strip()[:200]  # 限制长度
                                logger.debug(f"  描述: {description[:50]}...")
                    except Exception:
                        pass

                    # 确定最终的模型 ID（优先使用完整 ID）
                    final_id = full_model_id if full_model_id else model_name

                    model = ModelInfo(
                        id=final_id,
                        name=model_name,
                        vendor=vendor,
                        rank=i,
                        is_available=True,
                        test_status="pending",
                        is_downloadable=downloadable,
                        is_free_endpoint=free_endpoint,
                        tags=tags,
                        description=description
                    )
                    models.append(model)

                    # 打印详细信息（调试）
                    logger.debug(
                        f"Model #{i}: {final_id} | Vendor: {vendor} | "
                        f"Tags: {tags} | Downloadable: {downloadable} | Free: {free_endpoint}"
                    )

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

    async def _close_cookie_consent(self):
        """关闭 OneTrust Cookie 同意弹窗（如果存在）

        NVIDIA 网站使用 OneTrust Cookie 同意弹窗，会阻挡页面元素的点击操作。
        此方法在关键操作前调用以确保弹窗不会干扰。
        """
        try:
            # 查找并点击 "Accept All" 或类似按钮
            accept_selectors = [
                '#onetrust-accept-btn-handler',  # Accept All 按钮
                '.onetrust-close-btn-handler',   # 关闭按钮
                'button[id*="accept"]',           # 通用接受按钮
                '[class*="cookie"] button:first-child',  # Cookie 弹窗中的第一个按钮
            ]

            for selector in accept_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        logger.info("✅ 已关闭 Cookie 同意弹窗")
                        await self.page.wait_for_timeout(1000)
                        return True
                except Exception:
                    continue

            # 如果找不到按钮，尝试按 ESC 键关闭弹窗
            await self.page.keyboard.press('Escape')
            await self.page.wait_for_timeout(500)

        except Exception as e:
            logger.debug(f"关闭弹窗时出错（可忽略）: {e}")

        return False

    async def _go_to_next_page(self) -> bool:
        """点击下一页按钮进行翻页

        NVIDIA 网站使用传统分页系统，通过点击"下一页"按钮进行翻页。
        相比滚动加载，这种方式更可靠且可预测。

        Returns:
            bool: 是否成功翻页（True=成功翻页, False=已到末页或失败）
        """
        try:
            # 关闭可能出现的 Cookie 弹窗（防止阻挡点击）
            await self._close_cookie_consent()

            # 定位下一页按钮（使用 aria-label 属性）
            next_button = await self.page.query_selector('button[aria-label="Go to next page"]')

            if not next_button:
                logger.debug("未找到下一页按钮（可能已到达最后一页）")
                return False

            # 检查按钮是否被禁用
            is_disabled = await next_button.evaluate("el => el.disabled || el.getAttribute('aria-disabled') === 'true'")
            if is_disabled:
                logger.debug("下一页按钮已禁用（已到达最后一页）")
                return False

            # 点击下一页按钮
            logger.info("点击下一页按钮...")
            await next_button.click()

            # 等待页面加载完成（2-3秒让新内容渲染）
            await self.page.wait_for_timeout(2500)

            # 额外等待网络空闲
            try:
                await self.page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # 超时也继续

            logger.info("✅ 成功翻页")
            return True

        except Exception as e:
            logger.warning(f"翻页操作失败: {e}")
            return False

    async def _scroll_for_more(self) -> bool:
        """滚动页面以加载更多模型（增强版）- 已废弃，改用 _go_to_next_page()

        保留此方法作为备用方案，但主循环已切换到分页模式。
        如果未来 NVIDIA 网站改回无限滚动模式，可以取消注释恢复此方法。

        Returns:
            bool: 是否成功触发加载（不依赖loading indicator）
        """
        # ===== 以下实现已废弃，改用分页模式 =====
        # try:
        #     scroll_height_before = await self.page.evaluate("document.body.scrollHeight")
        #
        #     # 策略：多次小幅度滚动 + 等待（而非一次性滚到底部）
        #     for scroll_step in range(3):
        #         await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        #         await self.page.wait_for_timeout(1500)
        #
        #     # 额外等待，确保动态内容加载
        #     await self.page.wait_for_timeout(2000)
        #
        #     scroll_height_after = await self.page.evaluate("document.body.scrollHeight")
        #
        #     # 检测是否有新内容（scrollHeight变化说明加载了新内容）
        #     has_new_content = scroll_height_after > scroll_height_before
        #
        #     if has_new_content:
        #         logger.debug(f"滚动成功: 页面高度 {scroll_height_before} -> {scroll_height_after}")
        #         return True
        #     else:
        #         logger.debug(f"滚动后无新内容 (高度: {scroll_height_after})")
        #         return False
        #
        # except Exception as e:
        #     logger.warning(f"滚动失败: {e}")
        #     return False
        # ===== 废弃代码结束 =====

        # 返回 False 表示此方法已不可用，应使用 _go_to_next_page()
        logger.warning("_scroll_for_more() 已废弃，请使用 _go_to_next_page() 进行翻页")
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
        # 根据排序方式构建 URL（使用pageSize=96减少分页次数）
        # NVIDIA 默认每页24个模型，设置pageSize=96可将总页数从8页降至2页
        if sort_by == "popular":
            url = "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC&pageSize=96"
        else:  # recent
            url = "https://build.nvidia.com/models?pageSize=96"

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