import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_api_key():
    return "test-api-key-12345"


def test_nvidia_client_importable():
    import src.nvidia_client as nc
    assert hasattr(nc, 'NvidiaClient')
    assert callable(nc.NvidiaClient)


def test_nvidia_client_has_free_models():
    from src.nvidia_client import NvidiaClient
    assert hasattr(NvidiaClient, 'FREE_MODELS')
    assert isinstance(NvidiaClient.FREE_MODELS, dict)
    assert len(NvidiaClient.FREE_MODELS) > 0


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
    from src.nvidia_client import NvidiaClient
    client = NvidiaClient(api_key=mock_api_key)
    assert client.api_key == mock_api_key
    assert client.base_url is not None


def test_nvidia_client_list_models_returns_modelinfo(mock_api_key):
    from src.nvidia_client import NvidiaClient
    from src.models import ModelInfo
    client = NvidiaClient(api_key=mock_api_key)
    models = client.list_models()
    assert isinstance(models, list)
    if len(models) > 0:
        assert isinstance(models[0], ModelInfo), \
            f"list_models() should return List[ModelInfo], got {type(models[0])}"
