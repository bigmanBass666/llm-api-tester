"""DEPRECATED: 此模块的基类将被 platforms.base.base_client.BasePlatformClient 取代

新的代码应使用:
- 数据模型: from src.models import ModelInfo, ChatMessage, TestResult, TestReport
- 客户端基类: from platforms.base.base_client import BasePlatformClient

此文件保留仅为了向后兼容。
"""

import warnings
from abc import ABC, abstractmethod
from typing import Iterator, List

from src.models import ModelInfo, ChatMessage


class BaseClient(ABC):
    """DEPRECATED: 使用 platforms.base.base_client.BasePlatformClient 替代"""
    
    platform_name: str = "base"
    platform_display_name: str = "Base"

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url or getattr(self, 'BASE_URL', None)
        warnings.warn(
            "BaseClient is deprecated. Use BasePlatformClient from platforms.base.base_client instead.",
            DeprecationWarning,
            stacklevel=2
        )

    @abstractmethod
    def chat(self, model: str, messages: List[ChatMessage], **kwargs) -> str:
        """发送聊天请求"""
        pass

    @abstractmethod
    def chat_stream(self, model: str, messages: List[ChatMessage], **kwargs) -> Iterator[str]:
        """流式聊天"""
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """列出可用模型"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接"""
        pass

    def close(self):
        """关闭连接"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(platform={self.platform_name})>"
