"""
平台注册表
统一管理所有 API 平台，提供一致的调用接口
"""

from typing import Optional, Dict, List, Type, Callable
from dataclasses import dataclass, field

from .base_client import BaseClient, ChatMessage, ModelInfo


@dataclass
class PlatformConfig:
    """平台配置"""
    name: str  # 平台标识（nvidia, aliyun, etc.）
    display_name: str  # 显示名称
    client_class: Type[BaseClient]  # 客户端类
    default_base_url: Optional[str] = None  # 默认基础 URL
    api_key_env: Optional[str] = None  # API Key 环境变量名
    is_available: bool = True  # 是否可用
    description: str = ""  # 平台描述
    website: str = ""  # 官网


class PlatformRegistry:
    """平台注册表（单例）"""

    _instance: Optional['PlatformRegistry'] = None
    _platforms: Dict[str, PlatformConfig] = {}
    _default_client: Optional[BaseClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._platforms = {}
        return cls._instance

    def register(self, config: PlatformConfig) -> None:
        """注册平台"""
        self._platforms[config.name] = config

    def unregister(self, name: str) -> None:
        """取消注册平台"""
        if name in self._platforms:
            del self._platforms[name]

    def get(self, name: str) -> Optional[PlatformConfig]:
        """获取平台配置"""
        return self._platforms.get(name)

    def list_platforms(self) -> List[PlatformConfig]:
        """列出所有注册的平台"""
        return list(self._platforms.values())

    def list_available_platforms(self) -> List[PlatformConfig]:
        """列出所有可用的平台"""
        return [p for p in self._platforms.values() if p.is_available]

    def create_client(
        self,
        platform: str,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseClient:
        """
        创建平台客户端

        Args:
            platform: 平台标识
            api_key: API 密钥（如果为 None，尝试从环境变量获取）
            **kwargs: 其他配置

        Returns:
            客户端实例

        Raises:
            ValueError: 平台不存在
        """
        config = self._platforms.get(platform)
        if not config:
            raise ValueError(f"未知平台: {platform}，可用平台: {list(self._platforms.keys())}")

        # 如果没有提供 API Key，尝试从环境变量获取
        if api_key is None and config.api_key_env:
            import os
            api_key = os.environ.get(config.api_key_env)

        if api_key is None:
            raise ValueError(f"平台 {platform} 需要 API Key")

        return config.client_class(
            api_key=api_key,
            base_url=config.default_base_url,
            **kwargs
        )

    def set_default_platform(self, platform: str, api_key: Optional[str] = None, **kwargs) -> None:
        """
        设置默认平台

        Args:
            platform: 平台标识
            api_key: API 密钥
            **kwargs: 其他配置
        """
        self._default_client = self.create_client(platform, api_key, **kwargs)

    @property
    def default_client(self) -> Optional[BaseClient]:
        """获取默认客户端"""
        return self._default_client


# 全局注册表实例
registry = PlatformRegistry()


def register_platform(
    name: str,
    display_name: str,
    client_class: Type[BaseClient],
    default_base_url: Optional[str] = None,
    api_key_env: Optional[str] = None,
    is_available: bool = True,
    description: str = "",
    website: str = ""
) -> Callable:
    """
    平台注册装饰器

    用法:
        @register_platform(
            name="nvidia",
            display_name="NVIDIA NIM",
            client_class=NvidiaClient,
            api_key_env="NVIDIA_API_KEY"
        )
        class NvidiaClient(BaseClient):
            ...
    """
    def decorator(cls: Type[BaseClient]) -> Type[BaseClient]:
        config = PlatformConfig(
            name=name,
            display_name=display_name,
            client_class=cls,
            default_base_url=default_base_url,
            api_key_env=api_key_env,
            is_available=is_available,
            description=description,
            website=website
        )
        registry.register(config)
        cls.platform_name = name
        cls.platform_display_name = display_name
        return cls

    return decorator


# 统一调用接口
def chat(
    model: str,
    message: str,
    system: Optional[str] = None,
    platform: Optional[str] = None,
    **kwargs
) -> str:
    """
    统一聊天接口

    Args:
        model: 模型标识
        message: 用户消息
        system: 系统提示（可选）
        platform: 平台标识（可选，如果未指定则使用默认平台）
        **kwargs: 其他参数

    Returns:
        模型回复
    """
    if platform:
        client = registry.create_client(platform)
    elif registry.default_client:
        client = registry.default_client
    else:
        raise ValueError("未设置默认平台，请先调用 use_platform() 或提供 platform 参数")

    messages = []
    if system:
        messages.append(ChatMessage(role="system", content=system))
    messages.append(ChatMessage(role="user", content=message))

    return client.chat(model, messages, **kwargs)


def use_platform(platform: str, api_key: Optional[str] = None, **kwargs) -> None:
    """
    设置默认平台

    Args:
        platform: 平台标识
        api_key: API 密钥
        **kwargs: 其他配置
    """
    registry.set_default_platform(platform, api_key, **kwargs)


def list_models(platform: Optional[str] = None) -> List[ModelInfo]:
    """
    列出可用模型

    Args:
        platform: 平台标识（可选）

    Returns:
        模型列表
    """
    if platform:
        client = registry.create_client(platform)
        return client.list_models()
    elif registry.default_client:
        return registry.default_client.list_models()
    else:
        raise ValueError("未设置平台，请先调用 use_platform()")


def test_connection(platform: str, api_key: Optional[str] = None, **kwargs) -> bool:
    """
    测试平台连接

    Args:
        platform: 平台标识
        api_key: API 密钥
        **kwargs: 其他配置

    Returns:
        连接是否成功
    """
    client = registry.create_client(platform, api_key, **kwargs)
    return client.test_connection()