"""
API 客户端基类
定义统一客户端接口
"""

from abc import ABC, abstractmethod
from typing import List, Iterator
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ChatMessage


class BasePlatformClient(ABC):
    """API 客户端基类，所有平台客户端需继承此类"""

    platform_name: str = "base"

    @abstractmethod
    def chat(self, model: str, messages: List[ChatMessage], **kwargs) -> str:
        """
        发送聊天请求
        Args:
            model: 模型ID
            messages: 消息列表
            **kwargs: 其他参数（max_tokens, temperature 等）
        Returns:
            模型回复文本
        """
        pass

    @abstractmethod
    def list_models(self) -> List[dict]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    def close(self):
        """关闭客户端"""
        pass

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            models = self.list_models()
            return len(models) > 0
        except Exception:
            return False