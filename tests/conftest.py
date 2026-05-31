"""Pytest 全局 fixtures — 为核心模块单元测试提供 mock 环境"""

import pytest
from src.models import TestResult


@pytest.fixture(scope="session")
def mock_api_key():
    """Mock NVIDIA API Key"""
    return "nvapi-test-mock-key-for-unit-tests"


@pytest.fixture(scope="session")
def mock_base_url():
    """Mock NVIDIA Base URL"""
    return "https://integrate.api.nvidia.com/v1"


@pytest.fixture
def sample_model_info():
    """返回一个标准的 ModelInfo 实例用于测试"""
    from src.models import ModelInfo, ModelType
    return ModelInfo(
        id="test/model-id",
        name="Test Model",
        model_type=ModelType.TEXT,
        vendor="test",
        rank=1,
        is_free_endpoint=True,
        is_downloadable=False,
    )


@pytest.fixture
def sample_reasoning_model():
    """返回一个推理模型 ModelInfo（仅身份字段，无测试状态）"""
    from src.models import ModelInfo
    return ModelInfo(
        id="deepseek-ai/deepseek-v4-flash",
        name="DeepSeek V4 Flash",
        vendor="deepseek-ai",
        rank=10,
        is_reasoning=True,
    )


@pytest.fixture
def sample_test_result_success():
    """返回一个成功的 TestResult"""
    return TestResult(
        model_id="test/success-model",
        status="success",
        response_time=1.5,
        token_usage=100,
    )


@pytest.fixture
def sample_test_result_failed():
    """返回一个失败的 TestResult"""
    return TestResult(
        model_id="test/failed-model",
        status="failed",
        error_message="Model not found (404)",
    )


@pytest.fixture
def sample_test_result_timeout():
    """返回一个超时的 TestResult"""
    return TestResult(
        model_id="test/timeout-model",
        status="timeout",
        response_time=180.0,
        error_message="Request timed out",
    )


# 向后兼容别名（Phase 5 后删除）
sample_success_model = sample_test_result_success
sample_failed_model = sample_test_result_failed
sample_timeout_model = sample_test_result_timeout
