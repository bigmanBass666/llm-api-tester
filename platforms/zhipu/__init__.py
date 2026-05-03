"""
智谱平台模块
"""

from .client import ZhipuClient
from .scraper import ZhipuScraper
from .tester import ZhipuTester

SPEC = {
    "name": "zhipu",
    "display_name": "智谱 GLM",
    "scraper_cls": "ZhipuScraper",
    "tester_cls": "ZhipuTester",
    "legacy_mode": False,
    "capabilities": [],
}

__all__ = ['ZhipuClient', 'ZhipuScraper', 'ZhipuTester']