"""
API Testing Framework - 多平台 API 测试框架

支持 NVIDIA、智谱等多个平台的统一调用
"""

# 核心数据模型和配置
from .models import ModelInfo, ChatMessage
from .config_loader import ConfigLoader, load_config, get_api_key
from .ssl_config import setup_ssl_certificates

# 平台注册表（统一入口）
from .platform_registry import (
    PlatformRegistry,
    registry,
    register_platform,
    chat,
    use_platform,
    list_models,
    test_connection
)

__all__ = [
    # 核心类
    "ModelInfo",
    "ChatMessage",
    "ConfigLoader",

    # SSL 配置
    "setup_ssl_certificates",

    # 平台注册表
    "PlatformRegistry",
    "registry",
    "register_platform",

    # 统一接口
    "chat",
    "use_platform",
    "list_models",
    "test_connection",

    # 配置加载
    "load_config",
    "get_api_key",
]

# 向后兼容的便捷函数（延迟导入避免循环依赖）
def nvidia_chat(model: str, message: str, api_key: str = None, **kwargs) -> str:
    """NVIDIA 快速聊天（向后兼容）"""
    import os
    if api_key is None:
        api_key = os.environ.get("NVIDIA_API_KEY")

    from platforms.nvidia.client import NvidiaClient

    client = NvidiaClient(api_key=api_key)
    try:
        return client.chat(model, [ChatMessage(role="user", content=message)], **kwargs)
    finally:
        client.close()

def zhipu_chat(model: str, message: str, api_key: str = None, **kwargs) -> str:
    """智谱快速聊天（向后兼容）"""
    import os
    if api_key is None:
        api_key = os.environ.get("ZHIPU_API_KEY")

    from platforms.zhipu.client import ZhipuClient

    client = ZhipuClient(api_key=api_key)
    try:
        return client.chat(model, [ChatMessage(role="user", content=message)], **kwargs)
    finally:
        client.close()

__all__.extend(["nvidia_chat", "zhipu_chat"])

__version__ = "2.0.0"
