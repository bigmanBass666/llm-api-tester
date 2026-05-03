"""
NVIDIA 页面爬虫
爬取 build.nvidia.com 上的热门模型列表
继承 BaseScraper 基类，实现统一接口
"""

import asyncio
import os
import ssl
from typing import List, Dict, Optional
from playwright.async_api import async_playwright
import httpx

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ModelInfo
from platforms.base.base_scraper import BaseScraper


# 统一选择器常量
SELECTORS = {
    'card_root': "[data-testid='nv-card-root']",
    'vendor_link': "a[data-nvtrack-nav-object='artifact-card-publisher-link']",
    'model_link': "a[data-nvtrack-nav-object='artifact-card']",
    'badge': "[data-testid='nv-badge']",
    'next_page': 'button[aria-label="Go to next page"]',
}

# 文字模型过滤配置
TEXT_MODEL_CATEGORIES = {
    'text-generation', 'chat', 'coding', 'reasoning',
    'language generation', 'instruction following',
    'long-context', 'agentic', 'tool calling', 'moe'
}

NON_TEXT_KEYWORDS = [
    'whisper', 'flux', 'parakeet', 'stable-diffusion',
    'nemoretriever', 'esm2', 'nvclip', 'nemotron-parse',
    'riva-translate', 'magpie-tts', 'genmol', 'proteinmpnn',
    'rfdiffusion', 'shieldgemma', 'nemoguard', 'cosmos-',
    'nv-grounding', 'starcoder2', 'openfold', 'ipd/',
    'llama-nemotron-embed', 'nv-embed', 'nemotron-asr',
    'nemotron-ocr', 'nemotron-table', 'nemotron-page',
    'nemotron-graphic', 'parakeet-ctc', 'synthetic-video',
    'active-speaker', 'relighting', 'lipsync', 'embedding',
    'extraction', 'speech', 'asr', 'tts', 'vision-language'
]


class NvidiaScraper(BaseScraper):
    """NVIDIA 模型爬虫"""

    platform_name = "nvidia"

    # 配置常量
    _CONFIG = {
        'base_url': 'https://build.nvidia.com',
        'page_timeout_ms': 180000,
        'navigation_timeout_ms': 120000,
        'page_load_wait_ms': 3000,
        'pagination_wait_ms': 5000,
        'network_idle_timeout_ms': 10000,
        'max_page_turns': 10,
        'max_cards_per_page': 50,
        'api_timeout_s': 45.0,
        'api_connect_timeout_s': 15.0,
    }

    def __init__(self, headless: bool = True, filter_text_models: bool = False):
        self.headless = headless
        self.filter_text_models = filter_text_models
        self.browser = None
        self.page = None
        self._cookie_closed = False

    async def scrape(self, limit: int = 50, sort_by: str = "popular", sort_order: str = "DESC") -> List[ModelInfo]:
        """
        爬取模型列表（多页翻页 + 支持多种排序）

        Args:
            limit: 目标模型数量
            sort_by: 排序方式，'popular'(热度) 或 'recent'(最新)
            sort_order: 排序方向，'ASC' 或 'DESC'

        Returns:
            ModelInfo 列表
        """
        if sort_by not in ["popular", "recent"]:
            raise ValueError(f"不支持的排序方式: {sort_by}，可选值: popular, recent")

        # 构建 URL
        if sort_by == "popular":
            base_url = f"{self._CONFIG['base_url']}/models?orderBy=weightPopular%3ADESC"
            sort_name = "热度"
        else:  # recent
            base_url = f"{self._CONFIG['base_url']}/models"
            sort_name = "最新"

        print(f"🔍 NVIDIA: 开始获取模型列表 (目标: {limit} 个, 排序: {sort_name})")

        try:
            await self._init_browser()

            await self.page.goto(base_url, wait_until="networkidle")
            await self.page.wait_for_timeout(self._CONFIG['page_load_wait_ms'])

            await self._close_cookie_consent()

            api_model_map = await self._fetch_api_model_map()
            print(f"📡 API 可用模型: {len(api_model_map)} 个", flush=True)

            all_models = []
            current_page = 1
            max_pages = self._CONFIG['max_page_turns']
            filtered_count = 0

            while len(all_models) < limit and current_page <= max_pages:
                print(f"\n📄 正在爬取第 {current_page} 页...", flush=True)

                page_models = await self._extract_models()

                if not page_models:
                    print(f"⚠️ 第 {current_page} 页无模型，停止", flush=True)
                    break

                existing_ids = {m.id for m in all_models}
                new_models = []

                for model in page_models:
                    # 映射到 API ID
                    full_id = self._find_matching_model_id(model.id, api_model_map)
                    model.id = full_id
                    model.name = full_id.split("/")[-1] if "/" in full_id else full_id
                    model.vendor = full_id.split("/")[0] if "/" in full_id else "unknown"

                    # 去重
                    if model.id in existing_ids:
                        continue

                    # 文字模型过滤
                    if self.filter_text_models and not model.is_text_model:
                        filtered_count += 1
                        print(f"  🚫 过滤非文字模型: {model.id}", flush=True)
                        continue

                    # 设置排名
                    model.rank = len(all_models) + 1
                    new_models.append(model)
                    existing_ids.add(model.id)

                all_models.extend(new_models)
                print(f"   第{current_page}页: 获取 {len(page_models)} 个 (新增 {len(new_models)}个), 累计 {len(all_models)} 个", flush=True)

                # 检查是否没有新模型（可能到达最后一页）
                if len(new_models) == 0 and len(page_models) > 0 and current_page > 1:
                    print(f"   ⚠️ 本页模型已全部重复，可能到达最后一页", flush=True)
                    break

                # 翻页
                if len(all_models) < limit:
                    page_success = await self._go_to_next_page()
                    if not page_success:
                        print(f"   ⚠️ 翻页失败或已到达末页", flush=True)
                        break

                current_page += 1

            await self.close()

            final_models = all_models[:limit]

            if self.filter_text_models and filtered_count > 0:
                print(f"🚫 已过滤 {filtered_count} 个非文字模型")

            print(f"\n✅ 共获取 {len(final_models)} 个模型 ({current_page-1} 页)")
            return final_models

        except Exception as e:
            print(f"\n❌ 爬虫失败: {e}")
            await self.close()
            raise

    async def _extract_models(self) -> List[ModelInfo]:
        """
        从页面提取模型数据

        Returns:
            ModelInfo 列表
        """
        models = []

        try:
            # 使用统一选择器定位模型卡片
            model_cards = await self.page.query_selector_all(SELECTORS['card_root'])
            print(f"   找到 {len(model_cards)} 个模型卡片", flush=True)

            for i, card in enumerate(model_cards[:self._CONFIG['max_cards_per_page']], 1):
                try:
                    # 初始化默认值
                    model_name = f"unknown-{i}"
                    vendor = "unknown"
                    tags = []
                    downloadable = False
                    free_endpoint = True
                    full_model_id = None
                    category = None

                    # 提取完整模型 ID（优先从链接获取）
                    try:
                        card_link = await card.query_selector(SELECTORS['model_link'])
                        if card_link:
                            href = await card_link.get_attribute("href")
                            if href and href.startswith("/"):
                                full_model_id = href.lstrip("/")
                    except Exception:
                        pass

                    # 获取模型名称
                    try:
                        model_name_elem = await card.query_selector("h1, h2, h3, h4, h5")
                        if model_name_elem:
                            model_name = (await model_name_elem.text_content() or "").strip()

                        # 如果没有名称但获取到了完整ID，使用ID最后部分
                        if model_name == f"unknown-{i}" and full_model_id:
                            model_name = full_model_id.split("/")[-1] if "/" in full_model_id else full_model_id
                    except Exception:
                        pass

                    # 提取发布商信息
                    try:
                        vendor_link = await card.query_selector(SELECTORS['vendor_link'])
                        if vendor_link:
                            vendor_text = await vendor_link.text_content()
                            if vendor_text:
                                vendor = vendor_text.strip().lower().replace(" ", "-")
                        elif full_model_id and "/" in full_model_id:
                            vendor = full_model_id.split("/")[0]
                    except Exception:
                        if full_model_id and "/" in full_model_id:
                            vendor = full_model_id.split("/")[0]

                    # 提取标签
                    try:
                        badge_elements = await card.query_selector_all(SELECTORS['badge'])
                        for badge in badge_elements:
                            try:
                                tag_text = await badge.text_content()
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
                    except Exception:
                        pass

                    # 提取 Category Tag（从卡片 innerText 第5行）
                    try:
                        full_text = await card.inner_text()
                        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                        # lines 结构: [0]=Vendor, [1]=Badge, [2]=Model Name, [3]=Description, [4]=Category Tag
                        if len(lines) >= 5:
                            category = lines[4].lower()
                    except Exception:
                        pass

                    # 确定最终模型 ID
                    final_id = full_model_id if full_model_id else model_name

                    # 判断是否为文字模型
                    is_text = self._is_text_model_from_category(category, final_id)

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
                        category=category,
                        is_text_model=is_text
                    )
                    models.append(model)

                    # 打印前5个和最后一个的详情
                    if i <= 3 or i == len(model_cards):
                        tag_str = ", ".join(tags) if tags else "无"
                        print(f"  #{i}: {final_id} [{tag_str}]", flush=True)

                except Exception as e:
                    print(f"  ⚠️ 解析卡片 {i} 失败: {e}", flush=True)
                    continue

        except Exception as e:
            print(f"⚠️ 页面提取失败: {e}", flush=True)

        return models

    async def _fetch_api_model_map(self) -> Dict[str, str]:
        """
        从 NVIDIA API 获取模型 ID 映射表

        Returns:
            Dict[short_name, full_id] 例如: {"kimi-k2.5": "moonshotai/kimi-k2.5"}
        """
        api_url = "https://integrate.api.nvidia.com/v1/models"
        api_key = os.getenv("NVIDIA_API_KEY")

        model_map = {}

        if not api_key:
            print("⚠️ 未设置 NVIDIA_API_KEY，无法获取 API 模型映射")
            return model_map

        max_retries = 3
        retry_delay = 2

        for attempt in range(1, max_retries + 1):
            try:
                # 创建自定义 SSL context（禁用证书验证）
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self._CONFIG['api_timeout_s'], connect=self._CONFIG['api_connect_timeout_s']),
                    verify=ssl_context
                ) as client:
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

                        print(f"✅ API 映射表: {len(model_map)} 个模型", flush=True)
                        return model_map
                    else:
                        print(f"⚠️ API 返回错误: HTTP {resp.status_code}", flush=True)

            except httpx.ConnectError as e:
                print(f"⚠️ 连接失败 (尝试 {attempt}/{max_retries}): {e}", flush=True)
            except httpx.TimeoutException as e:
                print(f"⚠️ 请求超时 (尝试 {attempt}/{max_retries}): {e}", flush=True)
            except Exception as e:
                print(f"⚠️ API 请求异常 ({type(e).__name__}): {e}", flush=True)

            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

        print(f"⚠️ 经过 {max_retries} 次尝试后仍无法获取 API 映射表")
        return model_map

    def _is_text_model_from_category(self, category: Optional[str], model_id: str) -> bool:
        """
        判断是否为文字模型

        使用双重策略:
        1. 优先根据 Category Tag 白名单判断
        2. 其次根据模型 ID 黑名单关键词判断

        Args:
            category: 模型分类标签
            model_id: 模型ID

        Returns:
            bool: 是否为文字模型
        """
        # 策略1: 基于 Category Tag 判断
        if category:
            if category in TEXT_MODEL_CATEGORIES:
                return True
            # 明确的非文字类型标签
            if any(kw in category for kw in ['embedding', 'extraction', 'speech', 'asr', 'tts', 'vision-language']):
                return False

        # 策略2: 基于模型 ID 关键词兜底判断
        model_id_lower = model_id.lower()
        for keyword in NON_TEXT_KEYWORDS:
            if keyword in model_id_lower:
                return False

        # 默认认为是文字模型
        return True

    async def _go_to_next_page(self) -> bool:
        """
        点击下一页按钮进行翻页

        Returns:
            bool: 是否成功翻页
        """
        try:
            # 关闭可能出现的 Cookie 弹窗
            await self._close_cookie_consent()

            # 定位下一页按钮
            next_button = await self.page.query_selector(SELECTORS['next_page'])

            if not next_button:
                return False

            # 检查按钮是否被禁用
            is_disabled = await next_button.evaluate("el => el.disabled || el.getAttribute('aria-disabled') === 'true'")
            if is_disabled:
                return False

            # 点击下一页按钮
            await next_button.click()

            # 等待页面加载
            await self.page.wait_for_timeout(self._CONFIG['pagination_wait_ms'])
            try:
                await self.page.wait_for_load_state("networkidle", timeout=self._CONFIG['network_idle_timeout_ms'])
            except Exception:
                pass

            return True

        except Exception as e:
            print(f"   ⚠️ 翻页操作失败: {e}", flush=True)
            return False

    async def _close_cookie_consent(self) -> bool:
        """
        关闭 OneTrust Cookie 同意弹窗

        Returns:
            bool: 是否成功关闭
        """
        if self._cookie_closed:
            return True

        try:
            # 使用 JavaScript 批量尝试关闭弹窗
            dismissed = await self.page.evaluate("""() => {
                const methods = [
                    () => {
                        const btn = document.querySelector('#onetrust-accept-btn-handler');
                        if (btn) { btn.click(); return 'accept'; }
                        return null;
                    },
                    () => {
                        const btn = document.querySelector('.onetrust-close-btn-handler');
                        if (btn) { btn.click(); return 'close'; }
                        return null;
                    },
                    () => {
                        const btn = document.querySelector('#onetrust-reject-all-handler');
                        if (btn) { btn.click(); return 'reject'; }
                        return null;
                    },
                    () => {
                        const banner = document.querySelector('#onetrust-banner-sdk');
                        if (banner) { banner.style.display = 'none'; return 'hide_banner'; }
                        return null;
                    },
                    () => {
                        const overlay = document.querySelector('.onetrust-pc-dark-filter');
                        if (overlay) { overlay.remove(); return 'remove_overlay'; }
                        return null;
                    }
                ];

                for (const method of methods) {
                    const result = method();
                    if (result) return result;
                }
                return 'none';
            }""")

            if dismissed != 'none':
                print(f"   🍪 关闭Cookie弹窗: {dismissed}", flush=True)
                await self.page.wait_for_timeout(500)
                self._cookie_closed = True
                return True

        except Exception:
            pass

        return False

    async def _init_browser(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--ignore-certificate-errors", "--ignore-certificate-errors-spki-list"]
        )
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(self._CONFIG['page_timeout_ms'])

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None

    def _find_matching_model_id(self, short_name: str, api_map: Dict[str, str]) -> str:
        """
        从 API 映射表中找到匹配的完整ID

        Args:
            short_name: 短名称
            api_map: 短名→完整ID 的映射表

        Returns:
            完整ID，如果找不到则返回原短名
        """
        # 精确匹配
        if short_name in api_map:
            return api_map[short_name]

        # 模糊匹配
        for key, full_id in api_map.items():
            if short_name.lower() in key.lower() or key.lower() in short_name.lower():
                return full_id

        # 都没匹配到，返回原名称
        return short_name


async def scrape_top_models(limit: int = 50, sort_by: str = "popular", filter_text_models: bool = False) -> List[ModelInfo]:
    """
    爬取前N个热门模型（便捷函数）

    Args:
        limit: 爬取的模型数量
        sort_by: 排序方式，'popular' 或 'recent'
        filter_text_models: 是否只爬取文字模型

    Returns:
        ModelInfo 列表
    """
    scraper = NvidiaScraper(headless=True, filter_text_models=filter_text_models)
    try:
        models = await scraper.scrape(limit=limit, sort_by=sort_by)
        return models
    finally:
        await scraper.close()


if __name__ == "__main__":
    async def test():
        models = await scrape_top_models(10)
        for m in models:
            print(f"#{m.rank:2d} {m.id} (vendor={m.vendor}, text={m.is_text_model})")

    asyncio.run(test())
