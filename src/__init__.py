"""
API Testing Framework - 多平台 API 测试框架

支持 NVIDIA、智谱等多个平台的统一调用
"""

# 核心数据模型和配置
from .models import ModelInfo, ChatMessage
from .config_loader import ConfigLoader, load_config, get_api_key
from .ssl_config import setup_ssl_certificates
from .model_classifier import ModelClassifier

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

__version__ = "2.0.0"
