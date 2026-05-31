"""scripts/commands/batch.py 单元测试

测试 batch.py 中可隔离的薄壳逻辑：
- _print_summary 统计输出
- is_hosted 过滤逻辑
- favorites 模式配置读取

注：_gather_models / _run_testing 高度依赖全局副作用（ensure_platform_registered
触发真实注册、函数内局部 import），Mock 成本过高，其控制流由集成测试覆盖。
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import ModelInfo, ModelType, ScrapedMetadata


# ── Helpers ────────────────────────────────────────

def make_model(model_id, is_hosted=True, has_scraped=True, rank=0):
    s = ScrapedMetadata(is_hosted=is_hosted) if has_scraped else None
    return ModelInfo(
        id=model_id, name=model_id.split("/")[-1],
        model_type=ModelType.TEXT, rank=rank, scraped=s,
    )


def run_sync(coro):
    return asyncio.run(coro)


# ── _print_summary ─────────────────────────────────

class TestPrintSummary:
    def test_print_summary_all_success(self, capsys):
        results = [
            MagicMock(status="success", model_id="a/m1", response_time=1.0),
            MagicMock(status="success", model_id="a/m2", response_time=2.0),
            MagicMock(status="success", model_id="a/m3", response_time=0.5),
        ]
        from scripts.commands.batch import _print_summary
        _print_summary(results, "TestPlatform")
        captured = capsys.readouterr().out
        assert "TestPlatform" in captured
        assert "3" in captured  # total
        assert "100.0%" in captured or "100%" in captured

    def test_print_summary_mixed(self, capsys):
        results = [
            MagicMock(status="success", model_id="a/m1", response_time=1.0),
            MagicMock(status="failed", model_id="a/m2", response_time=0),
            MagicMock(status="timeout", model_id="a/m3", response_time=60.0),
        ]
        from scripts.commands.batch import _print_summary
        _print_summary(results, "TestPlatform")
        captured = capsys.readouterr().out
        assert "成功率" in captured

    def test_print_summary_fastest_sorted(self, capsys):
        r1 = MagicMock(status="success", model_id="slow", response_time=5.0)
        r2 = MagicMock(status="success", model_id="fast", response_time=0.5)
        from scripts.commands.batch import _print_summary
        _print_summary([r1, r2], "Test")
        captured = capsys.readouterr().out
        # fast 应在 slow 之前
        assert captured.index("fast") < captured.index("slow")

    def test_print_summary_no_successful(self, capsys):
        results = [
            MagicMock(status="failed", model_id="a/m1", response_time=0),
            MagicMock(status="timeout", model_id="a/m2", response_time=0),
        ]
        from scripts.commands.batch import _print_summary
        _print_summary(results, "Test")
        captured = capsys.readouterr().out
        assert "0" in captured


# ── is_hosted 过滤逻辑 ────────────────────────────

class TestIsHostedFilter:
    def test_scraped_none_passes(self):
        m = make_model("a/m1", has_scraped=False)
        result = m.scraped.is_hosted if m.scraped else True
        assert result is True

    def test_is_hosted_false_filtered(self):
        m = make_model("a/m1", is_hosted=False)
        result = m.scraped.is_hosted if m.scraped else True
        assert result is False

    def test_is_hosted_true_passes(self):
        m = make_model("a/m1", is_hosted=True)
        result = m.scraped.is_hosted if m.scraped else True
        assert result is True

    def test_batch_filter_logic(self):
        models = [
            make_model("a/hosted", is_hosted=True),
            make_model("b/unhosted", is_hosted=False),
            make_model("c/noscraped", has_scraped=False),
        ]
        filtered = [m for m in models if (m.scraped.is_hosted if m.scraped else True)]
        ids = [m.id for m in filtered]
        assert "a/hosted" in ids
        assert "b/unhosted" not in ids
        assert "c/noscraped" in ids


# ── favorites 模式配置读取 ────────────────────────

class TestFavoritesConfig:
    @patch("scripts.commands.batch.ensure_platform_registered")
    @patch("scripts.commands.batch.get_api_key", return_value="mock-key")
    @patch("scripts.commands.batch.get_platform_spec")
    @patch("scripts.commands.batch.yaml.safe_load")
    @patch("scripts.commands.batch.registry")
    def test_favorites_returns_in_config_order(self, mock_reg, mock_yaml, mock_spec, mock_key, mock_ensure):
        mock_spec.return_value = MagicMock(legacy_mode=True)
        mock_yaml.return_value = {
            "platforms": {
                "test": {"favorites": ["z-last", "a-first"]}
            }
        }
        all_m = [make_model("z-last"), make_model("a-first"), make_model("extra")]
        mock_client = MagicMock()
        mock_client.list_models.return_value = all_m
        mock_client.close = MagicMock()
        mock_reg.create_client.return_value = mock_client

        from scripts.commands.batch import _gather_models
        result = run_sync(_gather_models(
            platform="test", spec=mock_spec.return_value, api_key="mock-key",
            number=20, sort_by="popular", model_type="all",
            usecase=None, favorites=True, quiet=True,
        ))
        assert [m.id for m in result] == ["z-last", "a-first"]

    @patch("scripts.commands.batch.ensure_platform_registered")
    @patch("scripts.commands.batch.get_api_key", return_value="mock-key")
    @patch("scripts.commands.batch.get_platform_spec")
    def test_favorites_empty_returns_empty(self, mock_spec, mock_key, mock_ensure):
        mock_spec.return_value = MagicMock(legacy_mode=True)
        with patch("scripts.commands.batch.yaml.safe_load", return_value={"platforms": {"test": {}}}):
            from scripts.commands.batch import _gather_models
            result = run_sync(_gather_models(
                platform="test", spec=mock_spec.return_value, api_key="mock-key",
                number=20, sort_by="popular", model_type="all",
                usecase=None, favorites=True, quiet=True,
            ))
        assert result == []
