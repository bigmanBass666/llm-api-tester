from abc import ABC, abstractmethod
from typing import AsyncIterator, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.models import ModelInfo, ChatMessage


class BasePlatformClient(ABC):
    """平台客户端基类 - 所有平台客户端的统一接口"""
    
    platform_name: str = "base"

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def chat(self, model: str, messages: List[ChatMessage], **kwargs) -> str:
        """发送聊天请求"""
        pass

    @abstractmethod
    async def chat_stream(self, model: str, messages: List[ChatMessage], **kwargs) -> AsyncIterator[str]:
        """流式聊天（异步迭代器）"""
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """列出可用模型 - 返回统一的 ModelInfo 对象列表"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """测试 API 连接是否正常"""
        pass

    @abstractmethod
    def close(self):
        """关闭客户端连接、释放资源"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(platform={self.platform_name})>"
