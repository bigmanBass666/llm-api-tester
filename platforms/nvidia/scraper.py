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
        self._cookie_dismissed = False

    async def scrape(self, limit: int = 50) -> List[ModelInfo]:
        """爬取模型列表（多页翻页 + 热度排序）"""
        print(f"🔍 NVIDIA: 开始获取热门模型 (目标: {limit} 个)")

        try:
            await self._init_browser()

            base_url = "https://build.nvidia.com/models?orderBy=weightPopular%3ADESC"
            
            await self.page.goto(base_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            await self._dismiss_cookie_popup()
            
            api_model_map = await self._fetch_api_model_map()
            print(f"📡 API 可用模型: {len(api_model_map)} 个", flush=True)

            all_models = []
            current_page = 1
            max_pages = 10

            while len(all_models) < limit and current_page <= max_pages:
                print(f"\n📄 正在爬取第 {current_page} 页...", flush=True)

                if current_page > 1:
                    page_url = f"{base_url}&page={current_page}"
                    print(f"   🔗 导航到: {page_url}", flush=True)
                    
                    try:
                        await self.page.goto(page_url, wait_until="networkidle", timeout=30000)
                        await self.page.wait_for_timeout(2000)
                    except Exception as e:
                        print(f"   ⚠️ 页面导航失败: {e}", flush=True)
                        break

                page_models = await self._extract_models_from_page()
                
                if not page_models:
                    print(f"⚠️ 第 {current_page} 页无模型，停止", flush=True)
                    break

                existing_ids_before = {m.id for m in all_models}
                new_page_models = []

                for pm in page_models:
                    api_id = self._convert_to_api_id(pm.id, pm.href, api_model_map)
                    
                    if api_id in existing_ids_before:
                        continue
                    
                    model = ModelInfo(
                        id=api_id,
                        name=pm.name,
                        vendor=api_id.split("/")[0] if "/" in api_id else pm.vendor,
                        rank=len(all_models) + 1,
                        is_downloadable=pm.is_downloadable,
                        is_free_endpoint=pm.is_free_endpoint,
                        tags=pm.tags
                    )
                    all_models.append(model)
                    new_page_models.append(model)

                print(f"   第{current_page}页: 获取 {len(page_models)} 个 (新增 {len(new_page_models)}个), 累计 {len(all_models)} 个", flush=True)
                
                if len(new_page_models) == 0 and len(page_models) > 0 and current_page > 1:
                    print(f"   ⚠️ 本页模型已全部重复，可能到达最后一页", flush=True)
                    break

                current_page += 1

            await self.close()

            final = all_models[:limit]
            print(f"\n✅ 共获取 {len(final)} 个模型 ({current_page-1} 页)")
            return final

        except Exception as e:
            print(f"\n❌ 爬虫失败: {e}")
            try:
                await self.close()
            except Exception:
                pass
            
            print("⚠️ 回退到 API 列表...")
            return await self._fetch_api_model_list()[:limit]

    async def _click_next_page(self) -> bool:
        """点击下一页按钮（使用 JS 点击绕过 OneTrust 弹窗拦截）"""
        try:
            if not self._cookie_dismissed:
                await self._dismiss_cookie_popup()
                self._cookie_dismissed = True
            
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(1000)

            url_before = self.page.url
            
            clicked = await self.page.evaluate("""() => {
                const arrows = document.querySelectorAll('button.nv-pagination-arrow-button');
                
                if (arrows.length >= 3) {
                    arrows[2].click();
                    return true;
                }
                
                if (arrows.length > 0) {
                    arrows[arrows.length - 1].click();
                    return true;
                }
                
                return false;
            }""")
            
            if not clicked:
                print(f"   ⚠️ 未找到翻页按钮", flush=True)
                return False
            
            try:
                await self.page.wait_for_function(
                    "url => url !== window.location.url",
                    url_before,
                    timeout=10000
                )
            except Exception:
                pass
            
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                await self.page.wait_for_timeout(2000)
            
            url_after = self.page.url
            
            if url_after != url_before or "page=" in url_after:
                print(f"   🔗 翻页成功: {url_after}", flush=True)
                return True
            else:
                print(f"   ⚠️ URL未变化: {url_after}", flush=True)
                return False
            
        except Exception as e:
            err_msg = str(e)
            
            if "Execution context was destroyed" in err_msg or "navigation" in err_msg.lower():
                print(f"   🔄 页面导航中，等待加载...", flush=True)
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    await self.page.wait_for_timeout(3000)
                
                current_url = self.page.url
                print(f"   🔗 导航完成: {current_url}", flush=True)
                return True
            
            print(f"   ⚠️ 翻页错误: {e}", flush=True)
            return False

    async def _dismiss_cookie_popup(self):
        """关闭 OneTrust Cookie 弹窗"""
        try:
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
                    },
                    () => {
                        const pc = document.querySelector('#onetrust-pc-sdk');
                        if (pc) { pc.style.display = 'none'; return 'hide_pc'; }
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
            
        except Exception:
            pass

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