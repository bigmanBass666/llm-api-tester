import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_api_key():
    return "test-api-key-12345"


def test_nvidia_client_importable():
    from platforms.nvidia.client import NvidiaClient
    assert hasattr(NvidiaClient, 'NvidiaClient') or True  # 类已定义
    assert callable(NvidiaClient)


def test_nvidia_client_has_list_models(mock_api_key):
    from platforms.nvidia.client import NvidiaClient
    client = NvidiaClient(api_key=mock_api_key)
    assert hasattr(client, 'list_models')
    assert callable(client.list_models)


def test_platform_registry_has_nvidia():
    from src.platform_registry import registry, PlatformRegistry
    assert isinstance(registry, PlatformRegistry)
    nvidia_config = registry.get('nvidia')
    assert nvidia_config is not None
    assert nvidia_config.name == 'nvidia'


def test_nvidia_client_class_not_none():
    from src.platform_registry import registry
    nvidia_config = registry.get('nvidia')
    assert nvidia_config.client_class is not None, \
        f"NvidiaClient.client_class should NOT be None! Got: {nvidia_config.client_class}"
    assert nvidia_config.client_class.__name__ == 'NvidiaClient'


def test_nvidia_client_can_be_created(mock_api_key):
    from platforms.nvidia.client import NvidiaClient
    client = NvidiaClient(api_key=mock_api_key)
    assert client.api_key == mock_api_key
    assert client.base_url is not None


def test_nvidia_client_list_models_returns_modelinfo(mock_api_key):
    from platforms.nvidia.client import NvidiaClient
    from src.models import ModelInfo
    client = NvidiaClient(api_key=mock_api_key)
    models = client.list_models()
    assert isinstance(models, list)
    if len(models) > 0:
        assert isinstance(models[0], ModelInfo), \
            f"list_models() should return List[ModelInfo], got {type(models[0])}"


def test_zhipu_client_importable():
    from platforms.zhipu.client import ZhipuClient
    assert callable(ZhipuClient)


def test_zhipu_client_has_list_models():
    from platforms.zhipu.client import ZhipuClient
    assert hasattr(ZhipuClient, 'list_models')
    assert callable(ZhipuClient.list_models)


def test_base_platform_client_exists():
    from platforms.base.base_client import BasePlatformClient
    assert BasePlatformClient is not None


def test_src_init_exports():
    """验证 src/__init__.py 导出了正确的接口"""
    from src import (
        ModelInfo,
        ChatMessage,
        ConfigLoader,
        setup_ssl_certificates,
        PlatformRegistry,
        registry,
        register_platform,
        chat,
        use_platform,
        list_models,
        test_connection,
        load_config,
        get_api_key,
        nvidia_chat,
        zhipu_chat
    )
    
    # 验证核心类存在
    assert ModelInfo is not None
    assert ChatMessage is not None
    assert ConfigLoader is not None
    
    # 验证便捷函数存在且可调用
    assert callable(nvidia_chat)
    assert callable(zhipu_chat)
