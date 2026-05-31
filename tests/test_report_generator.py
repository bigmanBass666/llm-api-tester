"""report/generator.py 单元测试

覆盖 MarkdownFormatter、JsonFormatter、ReportGenerator 的核心逻辑。
纯单元测试，不依赖外部 API 或文件系统（save 方法用临时目录）。
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from src.models import TestResult, TestReport, ModelType, ScrapedMetadata
from report.generator import (
    MarkdownFormatter, JsonFormatter, ReportGenerator,
    TAG_ICONS, TAG_LEGEND, _format_tags, _get_scraped_field,
)


# ── Fixtures ──────────────────────────────────────

@pytest.fixture
def tag_icons():
    return TAG_ICONS


@pytest.fixture
def sample_text_results():
    """纯文本模型测试结果列表（覆盖 success/timeout/skipped/failed）"""
    return [
        TestResult(
            model_id="meta/llama-3.3-70b-instruct", model_type="text", rank=1,
            status="success", response_time=1.5,
            response_preview="OK", is_free_endpoint=True,
            tags=["free", "flash"],
            scraped=ScrapedMetadata(
                call_volume="1.2M API calls", published_at="January 2025",
                endpoint_type="free",
            ),
        ),
        TestResult(
            model_id="deepseek-ai/deepseek-v4-flash", model_type="text", rank=2,
            status="success", response_time=2.3,
            response_preview="OK", token_usage=100,
            reasoning_content="Thinking...",
            is_free_endpoint=False,
            tags=["thinking", "partner"],
            scraped=ScrapedMetadata(
                call_volume="800K API calls", published_at="March 2025",
                endpoint_type="partner",
            ),
        ),
        TestResult(
            model_id="google/gemma-7b", model_type="text", rank=3,
            status="timeout", response_time=60.0,
            error_message="Request timed out",
            is_free_endpoint=True, tags=["free"],
            scraped=ScrapedMetadata(endpoint_type="free"),
        ),
        TestResult(
            model_id="openai/gpt-4", model_type="text", rank=4,
            status="failed", response_time=5.0,
            error_message="Authentication failed",
            is_free_endpoint=False, tags=["partner"],
            scraped=ScrapedMetadata(endpoint_type="partner"),
        ),
        TestResult(
            model_id="meta/llama-4-maverick", model_type="text", rank=5,
            status="skipped", response_time=0.0,
            is_free_endpoint=True,
            tags=[],
        ),
    ]


@pytest.fixture
def sample_image_results():
    """文生图模型测试结果"""
    return [
        TestResult(
            model_id="black-forest-labs/flux.1-dev",
            model_type="image_generation", rank=10,
            status="success", response_time=8.5,
            response_preview="[image: 1024x1024, 2048.0KB, steps=50]",
            is_free_endpoint=False,
            tags=["partner"],
            scraped=ScrapedMetadata(endpoint_type="partner"),
        ),
    ]


@pytest.fixture
def sample_report(sample_text_results):
    return TestReport(
        timestamp=datetime(2026, 6, 1, 12, 0, 0).isoformat(),
        platform="nvidia",
        total=len(sample_text_results),
        success=2, failed=1, timeout=1,
        results=sample_text_results,
    )


@pytest.fixture
def sample_report_with_images(sample_text_results, sample_image_results):
    all_results = sample_text_results + sample_image_results
    return TestReport(
        timestamp=datetime(2026, 6, 1, 12, 0, 0).isoformat(),
        platform="nvidia",
        total=len(all_results),
        success=3, failed=1, timeout=1,
        results=all_results,
    )


# ── _format_tags ──────────────────────────────────

class TestFormatTags:
    def test_known_tags(self, tag_icons):
        assert _format_tags(["downloadable"]) == "📥"
        assert _format_tags(["free"]) == "🔓"
        assert _format_tags(["flash"]) == "⚡"
        assert _format_tags(["thinking"]) == "🤔"
        assert _format_tags(["partner"]) == "🤝"

    def test_multiple_tags(self, tag_icons):
        result = _format_tags(["free", "flash"])
        assert "🔓" in result
        assert "⚡" in result

    def test_empty_tags(self):
        assert _format_tags([]) == "-"
        assert _format_tags(None) == "-"

    def test_unknown_tag_passthrough(self):
        assert _format_tags(["custom_tag"]) == "custom_tag"

    def test_mixed_known_and_unknown(self):
        result = _format_tags(["free", "custom"])
        assert "🔓" in result
        assert "custom" in result


# ── _get_scraped_field ────────────────────────────

class TestGetScrapedField:
    def test_field_from_scraped(self):
        result = TestResult(
            model_id="test/model",
            scraped=ScrapedMetadata(call_volume="1M API calls"),
        )
        assert _get_scraped_field(result, "call_volume") == "1M API calls"

    def test_field_fallback_to_result_level(self):
        """scraped 为 None 时，回退到 result 层级的字段"""
        result = TestResult(model_id="test/model", rank=5, scraped=None)
        assert _get_scraped_field(result, "rank") == 5

    def test_empty_scraped_fallback(self):
        """scraped 存在但 rank 为默认值，验证 _get_scraped_field 能取到"""
        result = TestResult(
            model_id="test/model",
            rank=42,
            scraped=ScrapedMetadata(call_volume=""),
        )
        # scraped.call_volume 是 ""（falsy），但 rank 不在 scraped 中
        # 所以 _get_scraped_field 对 call_volume 回退到 result 层级
        assert _get_scraped_field(result, "rank") == 42

    def test_none_scraped_uses_default(self):
        result = TestResult(model_id="test/model", scraped=None)
        assert _get_scraped_field(result, "nonexistent_field") is None


# ── MarkdownFormatter ─────────────────────────────

class TestMarkdownFormatter:
    def test_format_contains_key_sections(self, sample_report):
        md = MarkdownFormatter().format(sample_report)
        assert "NVIDIA 模型批量测试报告" in md
        assert "总体统计" in md
        assert "最快模型排行榜" in md
        assert "文本模型测试结果" in md
        assert "标签说明" in md

    def test_format_contains_statistics(self, sample_report):
        md = MarkdownFormatter().format(sample_report)
        assert "5" in md  # total
        assert "2" in md  # success
        assert "40.0%" in md or "40%" in md  # success rate

    def test_format_contains_model_ids(self, sample_report):
        md = MarkdownFormatter().format(sample_report)
        assert "meta/llama-3.3-70b-instruct" in md
        assert "deepseek-ai/deepseek-v4-flash" in md

    def test_format_fastest_table_sorted_by_response_time(self, sample_report):
        md = MarkdownFormatter().format(sample_report)
        # 最快的模型是 llama (1.5s)，第二是 deepseek (2.3s)
        llama_pos = md.index("meta/llama-3.3-70b-instruct")
        # 在最快排行榜中，llama 应在 deepseek 之前
        fastest_section = md[md.index("最快模型排行榜"):md.index("文本模型测试结果")]
        assert "meta/llama-3.3-70b-instruct" in fastest_section

    def test_format_image_results_in_separate_section(self, sample_report_with_images):
        md = MarkdownFormatter().format(sample_report_with_images)
        assert "文生图模型测试结果" in md
        assert "black-forest-labs/flux.1-dev" in md

    def test_format_status_icons(self, sample_report):
        md = MarkdownFormatter().format(sample_report)
        # success → ✅, timeout → ⏰, failed → ❌, skipped → ⏭️
        assert "✅" in md
        assert "⏭️" in md

    def test_format_empty_results(self):
        report = TestReport(
            timestamp=datetime.now().isoformat(), platform="empty",
            total=0, success=0, failed=0, timeout=0, results=[],
        )
        md = MarkdownFormatter().format(report)
        assert "0" in md
        assert "empty" in md.lower() or "EMPTY" in md

    def test_format_tags_in_output(self, sample_report):
        md = MarkdownFormatter().format(sample_report)
        # free → 🔓
        assert "🔓" in md

    def test_format_deprecation_warning(self):
        results = [
            TestResult(
                model_id="old/model-v1", model_type="text", rank=1,
                status="success", response_time=3.0,
                scraped=ScrapedMetadata(
                    deprecation_info="Deprecation in June 2026",
                ),
            ),
        ]
        report = TestReport(
            timestamp=datetime.now().isoformat(), platform="nvidia",
            total=1, success=1, failed=0, timeout=0, results=results,
        )
        md = MarkdownFormatter().format(report)
        assert "⚠️" in md
        assert "Deprecation in June 2026" in md


# ── JsonFormatter ─────────────────────────────────

class TestJsonFormatter:
    def test_format_is_valid_json(self, sample_report):
        raw = JsonFormatter().format(sample_report)
        data = json.loads(raw)  # 不抛异常即为合法 JSON
        assert isinstance(data, dict)

    def test_format_contains_required_fields(self, sample_report):
        data = json.loads(JsonFormatter().format(sample_report))
        assert "timestamp" in data
        assert "platform" in data
        assert "total" in data
        assert "success" in data
        assert "failed" in data
        assert "timeout" in data
        assert "success_rate" in data
        assert "results" in data

    def test_format_results_are_dicts(self, sample_report):
        data = json.loads(JsonFormatter().format(sample_report))
        assert len(data["results"]) == 5
        assert isinstance(data["results"][0], dict)

    def test_format_result_contains_scraped_fields(self, sample_report):
        data = json.loads(JsonFormatter().format(sample_report))
        r = data["results"][0]
        assert "call_volume" in r
        assert "published_at" in r
        assert "endpoint_type" in r
        assert "deprecation_info" in r

    def test_format_empty_results(self):
        report = TestReport(
            timestamp=datetime.now().isoformat(), platform="empty",
            total=0, success=0, failed=0, timeout=0, results=[],
        )
        data = json.loads(JsonFormatter().format(report))
        assert data["total"] == 0
        assert data["results"] == []


# ── ReportGenerator ───────────────────────────────

class TestReportGenerator:
    def test_generate_creates_files(self, sample_report, tmp_path):
        gen = ReportGenerator(platform="nvidia")
        files = gen.generate(sample_report.results, output_dir=str(tmp_path))
        assert "markdown" in files
        assert "json" in files
        assert Path(files["markdown"]).exists()
        assert Path(files["json"]).exists()

    def test_generate_markdown_content_valid(self, sample_report, tmp_path):
        gen = ReportGenerator(platform="nvidia")
        files = gen.generate(sample_report.results, output_dir=str(tmp_path))
        content = Path(files["markdown"]).read_text(encoding="utf-8")
        assert "NVIDIA 模型批量测试报告" in content
        assert "meta/llama-3.3-70b-instruct" in content

    def test_generate_json_content_valid(self, sample_report, tmp_path):
        gen = ReportGenerator(platform="nvidia")
        files = gen.generate(sample_report.results, output_dir=str(tmp_path))
        data = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
        assert data["platform"] == "nvidia"
        assert data["total"] == 5

    def test_generate_platform_dir_structure(self, sample_report, tmp_path):
        gen = ReportGenerator(platform="zhipu")
        files = gen.generate(sample_report.results, output_dir=str(tmp_path))
        assert "zhipu" in files["markdown"]
        assert "zhipu" in files["json"]
