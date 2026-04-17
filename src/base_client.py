"""
API 客户端基类
定义统一接口，所有平台客户端需继承此类
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """模型信息"""
    id: str  # 模型标识
    name: str  # 显示名称
    platform: str  # 所属平台
    is_free: bool = True  # 是否免费
    is_reasoning: bool = False  # 是否推理模型
    max_tokens: int = 4096  # 最大输出token
    context_window: int = 128000  # 上下文窗口大小
    description: str = ""  # 模型描述


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # system, user, assistant
    content: str


class BaseClient(ABC):
    """API 客户端基类"""

    # 子类需要设置的平台标识
    platform_name: str = "base"
    platform_display_name: str = "Base"

    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        """
        初始化客户端

        Args:
            api_key: API 密钥
            base_url: API 基础 URL（可选）
            **kwargs: 其他配置参数
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs

    @abstractmethod
    def chat(
        self,
        model: str,
        messages: List[ChatMessage],
        **kwargs
    ) -> str:
        """
        发送聊天请求

        Args:
            model: 模型标识
            messages: 消息列表
            **kwargs: 其他参数（temperature, top_p, max_tokens 等）

        Returns:
            模型回复文本
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        model: str,
        messages: List[ChatMessage],
        **kwargs
    ) -> Iterator[str]:
        """
        流式聊天请求

        Args:
            model: 模型标识
            messages: 消息列表
            **kwargs: 其他参数

        Yields:
            回复片段
        """
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """
        获取可用模型列表

        Returns:
            模型信息列表
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        测试连接

        Returns:
            连接是否成功
        """
        pass

    def close(self):
        """关闭客户端（子类可重写）"""
        pass

    def __repr__(self) -> str:
        return f"<{self.platform_display_name}Client: {self.base_url or 'default'}>"