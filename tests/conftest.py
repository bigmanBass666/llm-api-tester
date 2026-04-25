"""Pytest 全局 fixtures — 为核心模块单元测试提供 mock 环境"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


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
    from src.models import ModelInfo, TestStatus
    return ModelInfo(
        id="test/model-id",
        name="Test Model",
        vendor="test",
        rank=1,
        is_text_model=True,
        is_free_endpoint=True,
        is_downloadable=False,
        test_status=TestStatus.PENDING.value,
    )


@pytest.fixture
def sample_success_model():
    """返回一个测试成功的 ModelInfo"""
    from src.models import ModelInfo, TestStatus
    return ModelInfo(
        id="test/success-model",
        name="Success Model",
        vendor="nvidia",
        rank=1,
        response_time=1.5,
        test_status=TestStatus.SUCCESS.value,
        token_usage=100,
    )


@pytest.fixture
def sample_failed_model():
    """返回一个测试失败的 ModelInfo"""
    from src.models import ModelInfo, TestStatus
    return ModelInfo(
        id="test/failed-model",
        name="Failed Model",
        vendor="nvidia",
        rank=2,
        error_message="Model not found (404)",
        test_status=TestStatus.FAILED.value,
    )


@pytest.fixture
def sample_timeout_model():
    """返回一个超时的 ModelInfo"""
    from src.models import ModelInfo, TestStatus
    return ModelInfo(
        id="test/timeout-model",
        name="Timeout Model",
        vendor="nvidia",
        rank=3,
        response_time=180.0,
        test_status=TestStatus.TIMEOUT.value,
        error_message="Request timed out",
    )


@pytest.fixture
def sample_reasoning_model():
    """返回一个推理模型 ModelInfo"""
    from src.models import ModelInfo, TestStatus
    return ModelInfo(
        id="deepseek-ai/deepseek-v4-flash",
        name="DeepSeek V4 Flash",
        vendor="deepseek-ai",
        rank=10,
        is_reasoning=True,
        reasoning_effort="high",
        test_status=TestStatus.SUCCESS.value,
        response_time=3.2,
        token_usage=500,
    )
