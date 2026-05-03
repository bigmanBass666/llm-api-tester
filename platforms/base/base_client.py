from abc import ABC, abstractmethod
from typing import AsyncIterator, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.models import ModelInfo, ChatMessage


class BasePlatformClient(ABC):
    """平台客户端基类 - 所有平台客户端的统一接口

    提供统一的初始化、SSL配置、错误处理等基础功能。
    所有平台客户端都应继承此类。
    """

    platform_name: str = "base"

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url

        # 统一的初始化流程
        self._setup_ssl_config()
        self._validate_config()

        # 调用子类的自定义初始化（如果存在）
        if hasattr(self, '_custom_init'):
            self._custom_init(**kwargs)

    def _setup_ssl_config(self):
        """统一的 SSL 配置初始化

        子类可覆盖此方法以实现自定义 SSL 配置。
        默认行为：尝试从 src.ssl_config 加载证书配置。
        """
        try:
            from src.ssl_config import setup_ssl_certificates
            setup_ssl_certificates()
        except ImportError:
            pass

    def _validate_config(self):
        """统一的配置验证

        子类可覆盖此方法以添加特定平台的验证逻辑。
        默认行为：检查 API Key 是否存在。
        """
        if not self.api_key and self.platform_name != "base":
            raise ValueError(f"{self.platform_name} 客户端需要 API Key")

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
