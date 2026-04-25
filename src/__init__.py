"""
API Testing Framework - 多平台 API 测试框架

支持 NVIDIA、阿里云、腾讯云、智谱等多个平台的统一调用
"""

from .base_client import BaseClient, ChatMessage, ModelInfo
from .ssl_config import setup_ssl_certificates, get_ssl_cert_path
from .platform_registry import (
    PlatformRegistry,
    registry,
    register_platform,
    chat,
    use_platform,
    list_models,
    test_connection
)
from .nvidia_client import NvidiaClient, nvidia_chat

# 导入所有平台客户端以触发注册
from . import nvidia_client
# from . import aliyun_client  # 待实现
# from . import tencent_client  # 待实现

__all__ = [
    # 核心类
    "BaseClient",
    "ChatMessage",
    "ModelInfo",
    "PlatformRegistry",
    "NvidiaClient",

    # SSL 配置
    "setup_ssl_certificates",
    "get_ssl_cert_path",

    # 平台注册表
    "registry",
    "register_platform",

    # 统一接口
    "chat",
    "use_platform",
    "list_models",
    "test_connection",

    # 便捷函数
    "nvidia_chat",
]

__version__ = "1.0.0"