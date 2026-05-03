"""
NVIDIA 平台模块
"""

from .scraper import NvidiaScraper
from .tester import NvidiaTester

SPEC = {
    "name": "nvidia",
    "display_name": "NVIDIA NIM",
    "scraper_cls": "NvidiaScraper",
    "tester_cls": "NvidiaTester",
    "legacy_mode": True,
    "capabilities": ["reasoning", "resume", "pagination"],
}

__all__ = ['NvidiaScraper', 'NvidiaTester']
