

from src.models import (
    ModelInfo,
    ChatMessage,
    TestResult,
    TestReport,
    TestStatus,
    ReasoningEffort,
    ModelType,
    ScrapedMetadata,
)

def test_model_info_defaults():
    m = ModelInfo(id="test", name="Test")
    assert m.id == "test"
    assert m.name == "Test"
    assert m.vendor == ""
    assert m.rank == 0
    assert m.is_available is True
    assert m.is_reasoning is False
    assert m.is_downloadable is False
    assert m.is_free_endpoint is True
    assert m.tags is None
    assert m.category is None
    assert m.is_text_model is True
    assert m.max_tokens == 4096
    assert m.context_window == 128000
    assert m.description == ""
    assert m.scraped is None


def test_model_info_to_dict():
    m = ModelInfo(
        id="gpt-4",
        name="GPT-4",
        vendor="OpenAI",
        rank=1,
        tags=["chat", "large"],
        category="reasoning",
        is_free_endpoint=True,
        is_downloadable=False,
    )
    d = m.to_dict()
    assert d["id"] == "gpt-4"
    assert d["name"] == "GPT-4"
    assert d["vendor"] == "OpenAI"
    assert d["rank"] == 1
    assert d["is_downloadable"] is False
    assert d["is_free_endpoint"] is True
    assert d["tags"] == ["chat", "large"]
    assert d["category"] == "reasoning"

def test_model_info_to_dict_empty_tags():
    m = ModelInfo(id="a", name="A", tags=None)
    d = m.to_dict()
    assert d["tags"] == []

def test_chat_message_to_dict():
    msg = ChatMessage(role="user", content="hello")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "hello"}

def test_chat_message_fields():
    msg = ChatMessage(role="assistant", content="hi there")
    assert msg.role == "assistant"
    assert msg.content == "hi there"

def test_test_result_defaults():
    r = TestResult(model_id="m1")
    assert r.model_id == "m1"
    assert r.rank == 0
    assert r.status == "pending"
    assert r.response_time == 0.0
    assert r.error_message == ""
    assert r.response_preview == ""
    assert r.is_downloadable is False
    assert r.is_free_endpoint is True
    assert r.tags is None
    assert r.reasoning_content == ""
    assert r.token_usage == 0
    assert r.scraped is None

def test_test_result_to_dict():
    r = TestResult(
        model_id="glm-4",
        rank=5,
        status="success",
        response_time=0.56789,
        error_message="",
        response_preview="OK response output here",
        is_downloadable=True,
        is_free_endpoint=True,
        tags=["free"],
        token_usage=42,
    )
    d = r.to_dict()
    assert d["model_id"] == "glm-4"
    assert d["rank"] == 5
    assert d["status"] == "success"
    assert d["response_time"] == 0.57
    assert d["error_message"] == ""
    assert d["response_preview"] == "OK response output here"
    assert d["is_downloadable"] is True
    assert d["is_free_endpoint"] is True
    assert d["tags"] == ["free"]
    assert d["token_usage"] == 42

def test_model_info_scraped_metadata():
    m = ModelInfo(
        id="meta/llama-3.3",
        name="llama-3.3",
        vendor="meta",
        scraped=ScrapedMetadata(created_at=1724000000, api_owned_by="meta"),
    )
    assert m.scraped.created_at == 1724000000
    assert m.scraped.api_owned_by == "meta"

def test_test_result_to_dict_includes_api_fields():
    r = TestResult(
        model_id="meta/llama-3.3",
        scraped=ScrapedMetadata(created_at=1724000000, api_owned_by="meta"),
    )
    d = r.to_dict()
    assert d["created_at"] == 1724000000
    assert d["api_owned_by"] == "meta"

def test_test_result_to_dict_truncation():
    long_preview = "y" * 200
    long_err = "z" * 250
    r = TestResult(
        model_id="x",
        response_preview=long_preview,
        error_message=long_err,
    )
    d = r.to_dict()
    assert len(d["response_preview"]) == 100
    assert len(d["error_message"]) == 200

def test_test_result_to_dict_empty_tags():
    r = TestResult(model_id="a", tags=None)
    d = r.to_dict()
    assert d["tags"] == []

def test_test_report_to_dict_basic():
    report = TestReport(
        timestamp="2026-04-25T12:00:00",
        platform="nvidia",
        total=10,
        success=8,
        failed=1,
        timeout=1,
        pending=0,
        duration=45.6789,
    )
    d = report.to_dict()
    assert d["timestamp"] == "2026-04-25T12:00:00"
    assert d["platform"] == "nvidia"
    assert d["duration_seconds"] == 45.68
    stats = d["statistics"]
    assert stats["total_models"] == 10
    assert stats["successful"] == 8
    assert stats["failed"] == 1
    assert stats["timeout"] == 1
    assert stats["pending"] == 0
    assert stats["success_rate"] == "80.0%"

def test_test_report_to_dict_zero_total():
    report = TestReport(timestamp="t", total=0, success=0)
    d = report.to_dict()
    assert d["statistics"]["success_rate"] == "N/A"

def test_test_report_to_dict_with_results():
    results = [
        TestResult(model_id="a", status="success"),
        TestResult(model_id="b", status="failed"),
    ]
    report = TestReport(timestamp="t", total=2, success=1, failed=1, results=results)
    d = report.to_dict()
    assert len(d["results"]) == 2
    assert d["results"][0]["model_id"] == "a"
    assert d["results"][0]["status"] == "success"
    assert d["results"][1]["model_id"] == "b"
    assert d["results"][1]["status"] == "failed"

def test_test_report_to_dict_raw_dicts_as_results():
    raw_results = [{"model_id": "x"}, {"model_id": "y"}]
    report = TestReport(timestamp="t", results=raw_results)
    d = report.to_dict()
    assert d["results"] == raw_results

def test_test_report_to_dict_none_results():
    report = TestReport(timestamp="t", results=None)
    d = report.to_dict()
    assert d["results"] == []

def test_enums_test_status_values():
    assert TestStatus.PENDING.value == "pending"
    assert TestStatus.TESTING.value == "testing"
    assert TestStatus.SUCCESS.value == "success"
    assert TestStatus.FAILED.value == "failed"
    assert TestStatus.TIMEOUT.value == "timeout"
    assert len(TestStatus) == 5

def test_enums_reasoning_effort_values():
    assert ReasoningEffort.LOW.value == "low"
    assert ReasoningEffort.MEDIUM.value == "medium"
    assert ReasoningEffort.HIGH.value == "high"
    assert len(ReasoningEffort) == 3

def test_enums_are_string_enums():
    assert isinstance(TestStatus.PENDING, str)
    assert isinstance(ReasoningEffort.HIGH, str)

def test_model_type_enum_values():
    assert ModelType.TEXT.value == "text"
    assert ModelType.IMAGE_GENERATION.value == "image_generation"
    assert ModelType.IMAGE_EDITING.value == "image_editing"
    assert ModelType.EMBEDDING.value == "embedding"
    assert ModelType.MULTIMODAL.value == "multimodal"
    assert ModelType.SPEECH.value == "speech"
    assert len(ModelType) == 6

def test_model_type_is_string_enum():
    assert isinstance(ModelType.TEXT, str)

def test_model_info_model_type_default():
    m = ModelInfo(id="a", name="A")
    assert m.model_type == ModelType.TEXT
    assert m.is_text_model is True

def test_model_info_model_type_image():
    m = ModelInfo(id="a", name="A", model_type=ModelType.IMAGE_GENERATION)
    assert m.model_type == ModelType.IMAGE_GENERATION
    assert m.is_text_model is False

def test_model_info_model_type_embedding():
    m = ModelInfo(id="a", name="A", model_type=ModelType.EMBEDDING)
    assert m.model_type == ModelType.EMBEDDING
    assert m.is_text_model is False

def test_model_info_to_dict_includes_is_text_model():
    m = ModelInfo(id="a", name="A", model_type=ModelType.IMAGE_GENERATION)
    d = m.to_dict()
    assert "is_text_model" in d
    assert d["is_text_model"] is False

def test_test_result_model_type_default():
    r = TestResult(model_id="m1")
    assert r.model_type == "text"

def test_test_result_model_type_image():
    r = TestResult(model_id="m1", model_type="image_generation")
    assert r.model_type == "image_generation"

def test_test_result_to_dict_includes_model_type():
    r = TestResult(model_id="m1", model_type="image_generation")
    d = r.to_dict()
    assert "model_type" in d
    assert d["model_type"] == "image_generation"


# ──────────────────────────────────────────────
# Phase 1: ScrapedMetadata + from_model_info()
# ──────────────────────────────────────────────

class TestScrapedMetadata:
    def test_defaults(self):
        sm = ScrapedMetadata()
        assert sm.call_volume == ""
        assert sm.published_at is None
        assert sm.deprecation_info is None
        assert sm.endpoint_type == "unknown"
        assert sm.is_hosted is None

    def test_construction(self):
        sm = ScrapedMetadata(call_volume="1M API calls", endpoint_type="free", is_hosted=True)
        assert sm.call_volume == "1M API calls"
        assert sm.endpoint_type == "free"
        assert sm.is_hosted is True

    def test_to_dict(self):
        sm = ScrapedMetadata(call_volume="100", created_at=1234567890)
        d = sm.to_dict()
        assert d["call_volume"] == "100"
        assert d["created_at"] == 1234567890
        assert d["is_hosted"] is None


class TestModelInfoScrapedProperty:
    def test_no_scraper_data_returns_none(self):
        m = ModelInfo(id="m1", name="test")
        assert m.scraped is None

    def test_with_scraper_data(self):
        m = ModelInfo(id="m1", name="test",
                       scraped=ScrapedMetadata(call_volume="1M", is_hosted=True))
        sm = m.scraped
        assert sm is not None
        assert sm.call_volume == "1M"
        assert sm.is_hosted is True

    def test_with_scraped_metadata(self):
        m = ModelInfo(id="m1", name="test", scraped=ScrapedMetadata(endpoint_type="free"))
        sm = m.scraped
        assert sm is not None
        assert sm.endpoint_type == "free"

    def test_with_created_at(self):
        m = ModelInfo(id="m1", name="test", scraped=ScrapedMetadata(created_at=1234567890))
        sm = m.scraped
        assert sm is not None
        assert sm.created_at == 1234567890


class TestResultFromModelInfo:
    def test_basic_copy(self):
        m = ModelInfo(id="m1", name="test", vendor="meta", rank=5,
                       model_type=ModelType.MULTIMODAL,
                       is_downloadable=True, is_free_endpoint=False,
                       tags=["free", "flash"])
        r = TestResult.from_model_info(m, status="success", response_time=1.5)
        assert r.model_id == "m1"
        assert r.model_type == "multimodal"
        assert r.rank == 5
        assert r.is_downloadable is True
        assert r.is_free_endpoint is False
        assert r.tags == ["free", "flash"]
        assert r.status == "success"
        assert r.response_time == 1.5

    def test_scraper_metadata_copied(self):
        m = ModelInfo(id="m1", name="test",
                       scraped=ScrapedMetadata(
                           call_volume="500K", endpoint_type="partner",
                           created_at=1234567890, api_owned_by="meta",
                           is_hosted=True))
        r = TestResult.from_model_info(m, status="success")
        assert r.scraped is not None
        assert r.scraped.call_volume == "500K"
        assert r.scraped.endpoint_type == "partner"
        assert r.scraped.created_at == 1234567890
        assert r.scraped.api_owned_by == "meta"
        assert r.scraped.is_hosted is True

    def test_scraped_metadata_field_set(self):
        m = ModelInfo(id="m1", name="test",
                       scraped=ScrapedMetadata(call_volume="100", is_hosted=True))
        r = TestResult.from_model_info(m, status="success")
        assert r.scraped is not None
        assert r.scraped.call_volume == "100"
        assert r.scraped.is_hosted is True

    def test_scraped_none_when_no_metadata(self):
        m = ModelInfo(id="m1", name="test")
        r = TestResult.from_model_info(m, status="success")
        assert r.scraped is None

    def test_test_fields_override_defaults(self):
        m = ModelInfo(id="m1", name="test")
        r = TestResult.from_model_info(m,
            status="timeout", response_time=30.0,
            error_message="timed out", token_usage=0)
        assert r.status == "timeout"
        assert r.response_time == 30.0
        assert r.error_message == "timed out"
