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
from crawler.models import is_reasoning_model


def create_tester(mock_api_key):
    """辅助函数: 创建 ModelTester 实例（绕过 __init__ 中的 SSL 和 API key 检查）"""
    tester = ModelTester.__new__(ModelTester)
    tester.api_key = mock_api_key
    tester.base_url = "https://integrate.api.nvidia.com/v1"
    tester.logger = None
    tester._client = None
    tester._http_client = None
    return tester


class TestModelTesterModeSelection:
    """测试模式选择逻辑 - 验证 force_normal/force_reasoning/auto_detect 三种模式"""

    @pytest.mark.asyncio
    async def test_mode_selection_normal(self, mock_api_key, sample_reasoning_model):
        """
        5.1 强制普通模式测试
        目标: 当 force_normal=True 时，即使模型是推理模型也应该使用普通模式
        场景: deepseek-v4-flash 是推理模型，但 force_normal=True 应该调用 _test_normal_model
        """
        tester = create_tester(mock_api_key)

        sample_reasoning_model.is_reasoning = False

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 50
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(tester, '_get_openai_client', return_value=mock_client):
            result = await tester.test_single_model(
                sample_reasoning_model,
                timeout=60,
                force_normal=True,
                force_reasoning=False
            )

            assert result.test_status == "success"
            assert not getattr(result, 'is_reasoning', False), \
                "force_normal=True 时不应设置 is_reasoning=True"

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
        场景: 普通模型在 force_reasoning=True 时应该调用 _test_reasoning_model
        """
        from src.models import ModelInfo, TestStatus

        normal_model = ModelInfo(
            id="google/gemma-7b",
            name="Gemma 7B",
            vendor="google",
            rank=5,
            test_status=TestStatus.PENDING.value,
        )

        tester = create_tester(mock_api_key)

        mock_client = AsyncMock()

        async def mock_stream():
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            delta1 = Mock()
            delta1.content = "OK"
            delta1.reasoning = None
            delta1.reasoning_content = None
            chunk1.choices[0].delta = delta1
            yield chunk1

        mock_response = mock_stream()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(tester, '_get_openai_client', return_value=mock_client):
            result = await tester.test_single_model(
                normal_model,
                timeout=60,
                force_reasoning=True,
                force_normal=False
            )

            assert result.test_status == "success"
            assert getattr(result, 'is_reasoning', False), \
                "force_reasoning=True 时应该设置 is_reasoning=True"

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
        场景:
          - 推理模型 (deepseek-v4-flash) 自动使用推理模式
          - 非推理模型 (gemma-7b) 自动使用普通模式
        """
        from src.models import ModelInfo, TestStatus

        reasoning_model = ModelInfo(
            id="deepseek-ai/deepseek-v4-flash",
            name="DeepSeek V4 Flash",
            vendor="deepseek-ai",
            rank=10,
            test_status=TestStatus.PENDING.value,
        )
        normal_model = ModelInfo(
            id="google/gemma-7b",
            name="Gemma 7B",
            vendor="google",
            rank=5,
            test_status=TestStatus.PENDING.value,
        )

        assert is_reasoning_model(reasoning_model.id), \
            "deepseek-v4-flash 应该被识别为推理模型"
        assert not is_reasoning_model(normal_model.id), \
            "gemma-7b 不应该被识别为推理模型"

        tester = create_tester(mock_api_key)

        mock_client = AsyncMock()

        async def mock_stream():
            chunk = Mock()
            chunk.choices = [Mock()]
            delta = Mock()
            delta.content = "OK"
            delta.reasoning = None
            delta.reasoning_content = None
            chunk.choices[0].delta = delta
            yield chunk

        mock_stream_response = mock_stream()
        mock_normal_response = Mock()
        mock_normal_response.usage = Mock()
        mock_normal_response.usage.total_tokens = 50

        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get('stream'):
                return mock_stream_response
            return mock_normal_response

        mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch.object(tester, '_get_openai_client', return_value=mock_client):

            reasoning_result = await tester.test_single_model(reasoning_model, timeout=60)
            assert reasoning_result.test_status == "success"
            assert getattr(reasoning_result, 'is_reasoning', False), \
                "推理模型自动检测后应使用推理模式"

            normal_result = await tester.test_single_model(normal_model, timeout=60)
            assert normal_result.test_status == "success"
            assert not getattr(normal_result, 'is_reasoning', False), \
                "非推理模型自动检测后应使用普通模式"


class TestModelTesterReportGeneration:
    """测试报告生成逻辑 - 验证统计、分类和排序"""

    def test_generate_report_success_only(self, sample_success_model):
        """
        5.4 全部成功时的报告生成测试
        目标:
          - summary 统计正确（total=success, failed=0, timeout=0）
          - successful_models 包含所有模型
          - failed_models 为空列表
        """
        from src.models import ModelInfo, TestStatus

        models = [
            ModelInfo(id="model/a", name="Model A", vendor="v1", rank=1,
                     response_time=1.0, token_usage=100, test_status=TestStatus.SUCCESS.value),
            ModelInfo(id="model/b", name="Model B", vendor="v2", rank=2,
                     response_time=2.0, token_usage=200, test_status=TestStatus.SUCCESS.value),
            ModelInfo(id="model/c", name="Model C", vendor="v3", rank=3,
                     response_time=1.5, token_usage=150, test_status=TestStatus.SUCCESS.value),
        ]

        report = ModelTester.generate_report(None, models)

        assert report['summary']['total'] == 3
        assert report['summary']['success'] == 3
        assert report['summary']['failed'] == 0
        assert report['summary']['timeout'] == 0

        assert len(report['successful_models']) == 3
        assert len(report['failed_models']) == 0

        model_ids = [m['id'] for m in report['successful_models']]
        assert set(model_ids) == {"model/a", "model/b", "model/c"}

    def test_generate_report_mixed(self, sample_failed_model, sample_timeout_model):
        """
        5.5 混合状态时的报告生成测试
        目标:
          - 成功/失败/超时状态统计正确
          - failed_models 包含 failed 和 timeout 状态的模型
          - 各类模型的详细信息完整
        """
        from src.models import ModelInfo, TestStatus

        models = [
            ModelInfo(id="model/success1", name="Success 1", vendor="v1", rank=1,
                     response_time=1.0, token_usage=100, test_status=TestStatus.SUCCESS.value),
            ModelInfo(id="model/success2", name="Success 2", vendor="v2", rank=2,
                     response_time=2.5, token_usage=200, test_status=TestStatus.SUCCESS.value),
            ModelInfo(id="model/failed1", name="Failed 1", vendor="v3", rank=3,
                     error_message="Authentication error", test_status=TestStatus.FAILED.value),
            ModelInfo(id="model/timeout1", name="Timeout 1", vendor="v4", rank=4,
                     response_time=180.0, error_message="Request timeout",
                     test_status=TestStatus.TIMEOUT.value),
            ModelInfo(id="model/pending1", name="Pending 1", vendor="v5", rank=5,
                     test_status=TestStatus.PENDING.value),
        ]

        report = ModelTester.generate_report(None, models)

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

        for fm in report['failed_models']:
            if fm['id'] == "model/failed1":
                assert fm['status'] == "failed"
                assert "Authentication" in fm['error']
            elif fm['id'] == "model/timeout1":
                assert fm['status'] == "timeout"
                assert "timeout" in fm['error'].lower()

    def test_generate_report_sorting(self):
        """
        5.6 报告排序测试
        目标:
          - successful_models 必须按 response_time 升序排列
          - 验证排序顺序正确性
        """
        from src.models import ModelInfo, TestStatus

        models = [
            ModelInfo(id="slow/model", name="Slow Model", vendor="v1", rank=1,
                     response_time=10.0, token_usage=500, test_status=TestStatus.SUCCESS.value),
            ModelInfo(id="fast/model", name="Fast Model", vendor="v2", rank=2,
                     response_time=0.5, token_usage=50, test_status=TestStatus.SUCCESS.value),
            ModelInfo(id="medium/model", name="Medium Model", vendor="v3", rank=3,
                     response_time=3.2, token_usage=200, test_status=TestStatus.SUCCESS.value),
            ModelInfo(id="very_fast/model", name="Very Fast", vendor="v4", rank=4,
                     response_time=0.1, token_usage=30, test_status=TestStatus.SUCCESS.value),
        ]

        report = ModelTester.generate_report(None, models)

        successful = report['successful_models']
        assert len(successful) == 4

        response_times = [m['response_time'] for m in successful]
        assert response_times == sorted(response_times), \
            f"successful_models 未按 response_time 升序排列，实际顺序: {response_times}"

        assert successful[0]['id'] == "very_fast/model"
        assert successful[0]['response_time'] == 0.1
        assert successful[1]['id'] == "fast/model"
        assert successful[1]['response_time'] == 0.5
        assert successful[2]['id'] == "medium/model"
        assert successful[2]['response_time'] == 3.2
        assert successful[3]['id'] == "slow/model"
        assert successful[3]['response_time'] == 10.0
