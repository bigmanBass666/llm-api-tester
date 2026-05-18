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
from src.models import ModelInfo, ModelType
from platforms.base.base_scraper import BaseScraper
from src.platform_config import PlatformConfigLoader


class NvidiaScraper(BaseScraper):
    """NVIDIA 模型爬虫"""

    platform_name = "nvidia"

    def __init__(self, headless: bool = True, model_type_filter: Optional['ModelType'] = None):
        self.headless = headless
        self.model_type_filter = model_type_filter
        self.browser = None
        self.page = None
        self._cookie_closed = False

        # 从配置加载器加载配置
        self._load_config()

    def _load_config(self):
        """从配置加载器加载配置"""
        config = PlatformConfigLoader.get_scraper_config(self.platform_name)
        if not config:
            raise ValueError(f"未找到 {self.platform_name} 平台的爬虫配置，请检查 configs/platforms.yaml")

        self._CONFIG = {
            'base_url': config.base_url,
            'page_timeout_ms': config.page_timeout_ms,
            'navigation_timeout_ms': config.navigation_timeout_ms,
            'page_load_wait_ms': config.page_load_wait_ms,
            'pagination_wait_ms': config.pagination_wait_ms,
            'network_idle_timeout_ms': config.network_idle_timeout_ms,
            'max_page_turns': config.max_page_turns,
            'page_size': config.page_size,
            'max_cards_per_page': config.max_cards_per_page,
            'api_timeout_s': config.api_timeout_s,
            'api_connect_timeout_s': config.api_connect_timeout_s,
        }

        self.SELECTORS = config.selectors
        self.TEXT_MODEL_CATEGORIES = config.text_model_categories
        self.NON_TEXT_KEYWORDS = config.non_text_keywords
        self.IMAGE_MODEL_CATEGORIES = config.image_model_categories
        self.IMAGE_MODEL_KEYWORDS = config.image_model_keywords
        self.MULTIMODAL_CATEGORIES = config.multimodal_categories
        self.MULTIMODAL_KEYWORDS = config.multimodal_keywords
        self.SPEECH_CATEGORIES = config.speech_categories
        self.SPEECH_KEYWORDS = config.speech_keywords
        self.USECASE_FILTERS = config.usecase_filters

    async def scrape(self, limit: int = 50, sort_by: str = "popular", sort_order: str = "DESC", usecase_filter: Optional[str] = None) -> List[ModelInfo]:
        """
        爬取模型列表（多页翻页 + 支持多种排序）

        Args:
            limit: 目标模型数量
            sort_by: 排序方式，'popular'(热度) 或 'recent'(最新)
            sort_order: 排序方向，'ASC' 或 'DESC'
            usecase_filter: 用例过滤，如 'text-generation', 'image-generation' 等

        Returns:
            ModelInfo 列表
        """
        if sort_by not in ["popular", "recent"]:
            raise ValueError(f"不支持的排序方式: {sort_by}，可选值: popular, recent")

        if sort_by == "popular":
            base_url = f"{self._CONFIG['base_url']}/models?orderBy=weightPopular%3ADESC&pageSize={self._CONFIG['page_size']}"
            sort_name = "热度"
        else:
            base_url = f"{self._CONFIG['base_url']}/models?pageSize={self._CONFIG['page_size']}"
            sort_name = "最新"

        if usecase_filter:
            filter_param = self.USECASE_FILTERS.get(usecase_filter, usecase_filter)
            encoded_filter = filter_param.replace(":", "%3A")
            base_url += f"&filters={encoded_filter}"
            sort_name += f" + 过滤:{filter_param}"

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
                existing_ids_before = set(existing_ids)
                new_models = []

                for model in page_models:
                    # 映射到 API ID
                    from platforms.common.utils import parse_model_id
                    full_id = self._find_matching_model_id(model.id, api_model_map)
                    model.id = full_id
                    id_vendor, short_name = parse_model_id(full_id)
                    model.name = short_name
                    model.vendor = id_vendor

                    # 用 API 元数据丰富模型信息
                    meta = api_model_map.get(f"__meta__:{full_id}")
                    if meta:
                        model.created_at = meta.get("created")
                        model.api_owned_by = meta.get("owned_by")

                    # 去重
                    if model.id in existing_ids:
                        continue

                    # 文字模型过滤
                    if self.model_type_filter is not None and model.model_type != self.model_type_filter:
                        filtered_count += 1
                        print(f"  🚫 过滤模型(类型不匹配): {model.id} ({model.model_type.value})", flush=True)
                        continue

                    # 设置排名
                    model.rank = len(all_models) + 1
                    new_models.append(model)
                    existing_ids.add(model.id)

                all_models.extend(new_models)
                print(f"   第{current_page}页: 获取 {len(page_models)} 个 (新增 {len(new_models)}个), 累计 {len(all_models)} 个", flush=True)

                page_new_ids = sum(1 for m in page_models if m.id not in existing_ids_before)
                if page_new_ids == 0 and len(page_models) > 0 and current_page > 1:
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

            if self.model_type_filter is not None and filtered_count > 0:
                print(f"🚫 已过滤 {filtered_count} 个类型不匹配的模型")

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
            model_cards = await self.page.query_selector_all(self.SELECTORS.get('card_root', "[data-testid='nv-card-root']"))
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
                        card_link = await card.query_selector(self.SELECTORS.get('model_link', "a[data-nvtrack-nav-object='artifact-card']"))
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
                        vendor_link = await card.query_selector(self.SELECTORS.get('vendor_link', "a[data-nvtrack-nav-object='artifact-card-publisher-link']"))
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
                        badge_elements = await card.query_selector_all(self.SELECTORS.get('badge', "[data-testid='nv-badge']"))
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

                    # 提取调用量和发布时间（从 span[aria-label] 属性）
                    call_volume = ""
                    published_at = None
                    try:
                        span_elements = await card.query_selector_all("span[aria-label]")
                        for span in span_elements:
                            aria_label = await span.get_attribute("aria-label")
                            if not aria_label:
                                continue
                            if "API calls" in aria_label:
                                call_volume = aria_label
                            elif any(m in aria_label for m in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]):
                                published_at = aria_label
                    except Exception:
                        pass

                    # 提取端点类型（Free/Partner Endpoint）
                    endpoint_type = "unknown"
                    try:
                        badge_elements = await card.query_selector_all(self.SELECTORS.get('badge', "[data-testid='nv-badge']"))
                        for badge in badge_elements:
                            try:
                                badge_text = await badge.text_content()
                                if badge_text:
                                    badge_lower = badge_text.strip().lower()
                                    if 'partner' in badge_lower or 'enterprise' in badge_lower:
                                        endpoint_type = "partner"
                                    elif 'free' in badge_lower:
                                        endpoint_type = "free"
                            except Exception:
                                continue
                        if endpoint_type == "unknown":
                            if free_endpoint:
                                endpoint_type = "free"
                            else:
                                endpoint_type = "partner"
                    except Exception:
                        pass

                    # 提取弃用警告（从卡片文本中匹配 "Deprecation in" 模式）
                    deprecation_info = None
                    try:
                        full_text_depr = await card.inner_text()
                        import re
                        depr_match = re.search(r'Deprecation\s+in\s+\w+\s+\d{4}', full_text_depr, re.IGNORECASE)
                        if depr_match:
                            deprecation_info = depr_match.group(0)
                    except Exception:
                        pass

                    # 确定最终模型 ID
                    final_id = full_model_id if full_model_id else model_name

                    # 判断是否为文字模型
                    from src.models import ModelType
                    classified_type = self._classify_model_type(category, final_id)

                    model = ModelInfo(
                        id=final_id,
                        name=model_name,
                        model_type=classified_type,
                        vendor=vendor,
                        rank=i,
                        is_available=True,
                        test_status="pending",
                        is_downloadable=downloadable,
                        is_free_endpoint=free_endpoint,
                        tags=tags,
                        category=category,
                        call_volume=call_volume,
                        published_at=published_at,
                        deprecation_info=deprecation_info,
                        endpoint_type=endpoint_type,
                    )
                    models.append(model)

                    # 打印前5个和最后一个的详情
                    if i <= 3 or i == len(model_cards):
                        tag_str = ", ".join(tags) if tags else "无"
                        cv_str = f" | 📞{call_volume}" if call_volume else ""
                        pub_str = f" | 📅{published_at}" if published_at else ""
                        print(f"  #{i}: {final_id} [{tag_str}]{cv_str}{pub_str}", flush=True)

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
                                from platforms.common.utils import parse_model_id
                                _, short_name = parse_model_id(full_id)
                                model_map[short_name] = full_id
                                model_map[full_id] = full_id
                                model_map[f"__meta__:{full_id}"] = {
                                    "created": m.get("created"),
                                    "owned_by": m.get("owned_by"),
                                }

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

    def _classify_model_type(self, category: Optional[str], model_id: str) -> 'ModelType':
        from src.models import ModelType
        if category:
            if category in self.IMAGE_MODEL_CATEGORIES:
                return ModelType.IMAGE_GENERATION
            if category in self.MULTIMODAL_CATEGORIES:
                return ModelType.MULTIMODAL
            if category in self.SPEECH_CATEGORIES:
                return ModelType.SPEECH
            if category in self.TEXT_MODEL_CATEGORIES:
                return ModelType.TEXT
            if any(kw in category for kw in ['embedding', 'extraction']):
                return ModelType.EMBEDDING
            if any(kw in category for kw in ['image-editing', 'image editing']):
                return ModelType.IMAGE_EDITING
        model_id_lower = model_id.lower()
        for keyword in self.IMAGE_MODEL_KEYWORDS:
            if keyword in model_id_lower:
                return ModelType.IMAGE_GENERATION
        for keyword in self.MULTIMODAL_KEYWORDS:
            if keyword in model_id_lower:
                return ModelType.MULTIMODAL
        for keyword in self.SPEECH_KEYWORDS:
            if keyword in model_id_lower:
                return ModelType.SPEECH
        for keyword in self.NON_TEXT_KEYWORDS:
            if keyword in model_id_lower:
                return ModelType.EMBEDDING
        return ModelType.TEXT

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
            next_button = await self.page.query_selector(self.SELECTORS.get('next_page', 'button[aria-label="Go to next page"]'))

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
            if short_name.lower() == key.lower():
                return full_id

        # 尝试下划线转点号（NVIDIA 特殊格式）
        fixed_name = short_name.replace('_', '.')
        if fixed_name in api_map:
            return api_map[fixed_name]

        # 返回原值（可能已经是完整 ID）
        return short_name


async def scrape_top_models(limit: int = 50, sort_by: str = "popular", model_type_filter: Optional['ModelType'] = None, usecase_filter: Optional[str] = None) -> List[ModelInfo]:
    """爬取前N个热门模型（便捷函数）

    Args:
        limit: 爬取的模型数量
        sort_by: 排序方式，'popular' 或 'recent'
        model_type_filter: 模型类型过滤（None=全部, ModelType.TEXT=仅文本, ModelType.IMAGE_GENERATION=仅文生图）
        usecase_filter: 用例过滤，如 'text-generation', 'image-generation' 等

    Returns:
        ModelInfo 列表
    """
    scraper = NvidiaScraper(headless=True, model_type_filter=model_type_filter)
    try:
        return await scraper.scrape(limit=limit, sort_by=sort_by, usecase_filter=usecase_filter)
    finally:
        await scraper.close()
