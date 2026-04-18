"""
爬虫基类
定义统一爬虫接口
"""

from abc import ABC, abstractmethod
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ModelInfo


class BaseScraper(ABC):
    """爬虫基类，所有平台爬虫需继承此类"""

    platform_name: str = "base"

    @abstractmethod
    async def scrape(self, limit: int = 50) -> List[ModelInfo]:
        """
        爬取模型列表
        Args:
            limit: 爬取数量
        Returns:
            模型信息列表
        """
        pass

    def log_progress(self, current: int, total: int, message: str = ""):
        """输出进度日志，格式：[current/total] message"""
        print(f"\r[{current}/{total}] {message}", end="", flush=True)