"""
ModelTester 单元测试 - 测试核心逻辑：模式选择和报告生成

覆盖场景：
- 模式选择逻辑（强制普通/推理/自动检测）
- 报告生成逻辑（统计/排序/分类）
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from crawler.tester import ModelTester
from src.model_classifier import is_reasoning_model
from src.models import ModelInfo, TestResult, TestStatus


def create_tester(mock_api_key):
    """辅助函数: 创建 ModelTester 实例（绕过 __init__ 中的 SSL 和 API key 检查）"""
    tester = ModelTester.__new__(ModelTester)
    tester.api_key = mock_api_key
    tester.base_url = "https://integrate.api.nvidia.com/v1"
    tester.logger = None
    tester._client = None
    tester._http_client = None
    return tester


def make_mock_normal_response():
    """创建普通模式的 mock 响应"""
    mock_response = Mock()
    mock_response.usage = Mock()
    mock_response.usage.total_tokens = 50
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "OK"
    return mock_response


async def make_mock_stream_response():
    """创建推理模式的 mock 流式响应"""
    chunk = Mock()
    chunk.choices = [Mock()]
    delta = Mock()
    delta.content = "OK"
    delta.reasoning = None
    delta.reasoning_content = None
    chunk.choices[0].delta = delta
    yield chunk


class TestModelTesterModeSelection:
    """测试模式选择逻辑 - 验证 force_normal/force_reasoning/auto_detect 三种模式"""

    @pytest.mark.asyncio
    async def test_mode_selection_normal(self, mock_api_key, sample_reasoning_model):
        """
        5.1 强制普通模式测试
        目标: 当 force_normal=True 时，即使模型是推理模型也应该使用普通模式
        """
        tester = create_tester(mock_api_key)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=make_mock_normal_response())

        with patch.object(tester, '_get_openai_client', return_value=mock_client):
            result = await tester.test_single_model(
                sample_reasoning_model,
                timeout=60,
                force_normal=True,
                force_reasoning=False
            )

            assert result.status == "success"
            assert isinstance(result, TestResult)

            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert 'stream' not in call_kwargs or call_kwargs.get('stream') is False, \
                "普通模式不应该使用流式输出"
            assert 'extra_body' not in call_kwargs, \
                "普通模式不应该包含 extra_body 参数"

    @pytest.mark.asyncio
    async def test_mode_selection_reasoning_force(self, mock_api_key):
        """
        5.2 强制推理模式测试
        目标: 当 force_reasoning=True 时，应该强制使用推理模式
        """
        normal_model = ModelInfo(
            id="google/gemma-7b", name="Gemma 7B", vendor="google", rank=5,
        )

        tester = create_tester(mock_api_key)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=make_mock_stream_response())

        with patch.object(tester, '_get_openai_client', return_value=mock_client):
            result = await tester.test_single_model(
                normal_model,
                timeout=60,
                force_reasoning=True,
                force_normal=False
            )

            assert result.status == "success"
            assert isinstance(result, TestResult)

            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs.get('stream') is True, \
                "推理模式应该使用流式输出"
            assert 'extra_body' in call_kwargs, \
                "推理模式应该包含 extra_body 参数"

    @pytest.mark.asyncio
    async def test_mode_selection_auto_detect(self, mock_api_key):
        """
        5.3 自动检测模式测试
        目标: 不指定 force 参数时，应该根据 is_reasoning_model() 自动检测模式
        """
        reasoning_model = ModelInfo(
            id="deepseek-ai/deepseek-v4-flash", name="DeepSeek V4 Flash",
            vendor="deepseek-ai", rank=10,
        )
        normal_model = ModelInfo(
            id="google/gemma-7b", name="Gemma 7B", vendor="google", rank=5,
        )

        assert is_reasoning_model(reasoning_model.id)
        assert not is_reasoning_model(normal_model.id)

        tester = create_tester(mock_api_key)

        mock_client = AsyncMock()

        async def mock_create(*args, **kwargs):
            if kwargs.get('stream'):
                return make_mock_stream_response()
            return make_mock_normal_response()

        mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch.object(tester, '_get_openai_client', return_value=mock_client):
            reasoning_result = await tester.test_single_model(reasoning_model, timeout=60)
            assert reasoning_result.status == "success"

            normal_result = await tester.test_single_model(normal_model, timeout=60)
            assert normal_result.status == "success"


class TestModelTesterReportGeneration:
    """测试报告生成逻辑 - 验证统计、分类和排序"""

    def test_generate_report_success_only(self):
        """5.4 全部成功时的报告生成测试"""
        results = [
            TestResult(model_id="model/a", rank=1, status="success",
                      response_time=1.0, token_usage=100),
            TestResult(model_id="model/b", rank=2, status="success",
                      response_time=2.0, token_usage=200),
            TestResult(model_id="model/c", rank=3, status="success",
                      response_time=1.5, token_usage=150),
        ]

        report = ModelTester.generate_report(None, results)

        assert report['summary']['total'] == 3
        assert report['summary']['success'] == 3
        assert report['summary']['failed'] == 0
        assert report['summary']['timeout'] == 0

        assert len(report['successful_models']) == 3
        assert len(report['failed_models']) == 0

        model_ids = [m['id'] for m in report['successful_models']]
        assert set(model_ids) == {"model/a", "model/b", "model/c"}

    def test_generate_report_mixed(self):
        """5.5 混合状态时的报告生成测试"""
        results = [
            TestResult(model_id="model/success1", rank=1, status="success",
                      response_time=1.0, token_usage=100),
            TestResult(model_id="model/success2", rank=2, status="success",
                      response_time=2.5, token_usage=200),
            TestResult(model_id="model/failed1", rank=3, status="failed",
                      error_message="Authentication error"),
            TestResult(model_id="model/timeout1", rank=4, status="timeout",
                      response_time=180.0, error_message="Request timeout"),
            TestResult(model_id="model/pending1", rank=5, status="pending"),
        ]

        report = ModelTester.generate_report(None, results)

        assert report['summary']['total'] == 5
        assert report['summary']['success'] == 2
        assert report['summary']['failed'] == 1
        assert report['summary']['timeout'] == 1
        assert report['summary']['pending'] == 1

        assert len(report['successful_models']) == 2
        assert len(report['failed_models']) == 2

        failed_ids = [m['id'] for m in report['failed_models']]
        assert "model/failed1" in failed_ids
        assert "model/timeout1" in failed_ids

        failed_statuses = {m['status'] for m in report['failed_models']}
        assert "failed" in failed_statuses
        assert "timeout" in failed_statuses

    def test_generate_report_sorting(self):
        """5.6 报告排序测试 - successful_models 按 response_time 升序"""
        results = [
            TestResult(model_id="slow/model", rank=1, status="success",
                      response_time=10.0, token_usage=500),
            TestResult(model_id="fast/model", rank=2, status="success",
                      response_time=0.5, token_usage=50),
            TestResult(model_id="medium/model", rank=3, status="success",
                      response_time=3.2, token_usage=200),
            TestResult(model_id="very_fast/model", rank=4, status="success",
                      response_time=0.1, token_usage=30),
        ]

        report = ModelTester.generate_report(None, results)

        successful = report['successful_models']
        assert len(successful) == 4

        response_times = [m['response_time'] for m in successful]
        assert response_times == sorted(response_times)

        assert successful[0]['id'] == "very_fast/model"
        assert successful[0]['response_time'] == 0.1
        assert successful[1]['id'] == "fast/model"
        assert successful[1]['response_time'] == 0.5
        assert successful[2]['id'] == "medium/model"
        assert successful[2]['response_time'] == 3.2
        assert successful[3]['id'] == "slow/model"
        assert successful[3]['response_time'] == 10.0
