import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import (
    ModelInfo,
    ChatMessage,
    TestResult,
    TestReport,
    TestStatus,
    ReasoningEffort,
)


def test_model_info_defaults():
    m = ModelInfo(id="test", name="Test")
    assert m.id == "test"
    assert m.name == "Test"
    assert m.vendor == ""
    assert m.rank == 0
    assert m.is_available is True
    assert m.is_reasoning is False
    assert m.test_status == "pending"
    assert m.response_time == 0.0
    assert m.error_message == ""
    assert m.token_usage == 0
    assert m.is_downloadable is False
    assert m.is_free_endpoint is True
    assert m.tags is None
    assert m.category is None
    assert m.is_text_model is True
    assert m.is_callable is False
    assert m.max_tokens == 4096
    assert m.context_window == 128000
    assert m.description == ""


def test_model_info_status_icon():
    assert ModelInfo(id="a", name="A", test_status="pending").status_icon == "\u23f3"
    assert ModelInfo(id="a", name="A", test_status="testing").status_icon == "\U0001f504"
    assert ModelInfo(id="a", name="A", test_status="success").status_icon == "\u2705"
    assert ModelInfo(id="a", name="A", test_status="failed").status_icon == "\u274c"
    assert ModelInfo(id="a", name="A", test_status="timeout").status_icon == "\u23f0"
    assert ModelInfo(id="a", name="A", test_status="unknown").status_icon == "\u2753"


def test_model_info_to_dict():
    m = ModelInfo(
        id="gpt-4",
        name="GPT-4",
        vendor="OpenAI",
        rank=1,
        test_status="success",
        response_time=1.23456,
        error_message="none",
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
    assert d["test_status"] == "success"
    assert d["response_time"] == 1.23
    assert d["is_callable"] is True
    assert d["is_downloadable"] is False
    assert d["is_free_endpoint"] is True
    assert d["tags"] == ["chat", "large"]
    assert d["category"] == "reasoning"
    assert d["error"] == "none"


def test_model_info_to_dict_error_truncation():
    long_err = "x" * 300
    m = ModelInfo(id="a", name="A", error_message=long_err)
    d = m.to_dict()
    assert len(d["error"]) == 200


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


def test_model_info_is_callable_pending():
    m = ModelInfo(id="a", name="A", test_status="pending")
    assert m.is_callable is False


def test_model_info_is_callable_success():
    m = ModelInfo(id="a", name="A", test_status="success")
    assert m.is_callable is True


def test_model_info_is_callable_failed():
    m = ModelInfo(id="a", name="A", test_status="failed")
    assert m.is_callable is False


def test_model_info_is_callable_timeout():
    m = ModelInfo(id="a", name="A", test_status="timeout")
    assert m.is_callable is False


def test_model_info_is_callable_testing():
    m = ModelInfo(id="a", name="A", test_status="testing")
    assert m.is_callable is False
