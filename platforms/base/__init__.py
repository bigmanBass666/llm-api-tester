"""
平台基类模块
定义所有平台的统一接口
"""

from .base_scraper import BaseScraper
from .base_tester import BaseTester
from .base_client import BasePlatformClient

__all__ = ['BaseScraper', 'BaseTester', 'BasePlatformClient']