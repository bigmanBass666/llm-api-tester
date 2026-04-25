import sys
import os
import importlib.util
import dataclasses

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_spec = importlib.util.spec_from_file_location(
    "crawler.models",
    os.path.join(os.path.dirname(__file__), "..", "crawler", "models.py"),
)
_module = importlib.util.module_from_spec(_spec)
_module.dataclass = dataclasses.dataclass
_module.field = dataclasses.field
sys.modules["crawler.models"] = _module
_spec.loader.exec_module(_module)

REASONING_MODELS = _module.REASONING_MODELS
REASONING_MODEL_PATTERNS = _module.REASONING_MODEL_PATTERNS
is_reasoning_model = _module.is_reasoning_model
get_reasoning_effort = _module.get_reasoning_effort


class TestIsReasoningModelExactMatch:
    def test_exact_match_deepseek_v4_flash(self):
        assert is_reasoning_model("deepseek-ai/deepseek-v4-flash") is True

    def test_exact_match_deepseek_v4_pro(self):
        assert is_reasoning_model("deepseek-ai/deepseek-v4-pro") is True

    def test_exact_match_glm51(self):
        assert is_reasoning_model("z-ai/glm-5.1") is True

    def test_exact_match_glm47(self):
        assert is_reasoning_model("z-ai/glm-4.7") is True


class TestIsReasoningModelPartialMatch:
    def test_partial_match_id_part(self):
        assert is_reasoning_model("deepseek-ai/deepseek-v4-flash") is True

    def test_partial_not_in_set_but_matches_pattern(self):
        assert is_reasoning_model("vendor/deepseek-v4-turbo") is True


class TestIsReasoningModelPattern:
    def test_pattern_deepseek(self):
        assert is_reasoning_model("some-vendor/deepseek-v4-new") is True

    def test_pattern_glm5(self):
        assert is_reasoning_model("vendor/glm-5.2-preview") is True

    def test_pattern_glm47(self):
        assert is_reasoning_model("x/glm-4.7-chat") is True

    def test_pattern_reasoning_keyword(self):
        assert is_reasoning_model("vendor/reasoning-model-v1") is True

    def test_pattern_thinking_keyword(self):
        assert is_reasoning_model("vendor/thinking-model") is True


class TestIsReasoningModelCaseInsensitive:
    def test_case_insensitive_uppercase(self):
        assert is_reasoning_model("DEEPSEEK-AI/DEEPSEEK-V4-FLASH") is True
        assert is_reasoning_model("Z-AI/GLM-5.1") is True

    def test_case_insensitive_mixed(self):
        assert is_reasoning_model("DeepSeek-AI/DeepSeek-V4-Pro") is True
        assert is_reasoning_model("Z-Ai/Glm-4.7") is True


class TestIsReasoningModelNegative:
    def test_normal_models_return_false(self):
        assert is_reasoning_model("qwen/qwen3-coder-480b-a35b-instruct") is False
        assert is_reasoning_model("google/gemma-7b") is False
        assert is_reasoning_model("meta/llama-3.1-8b-instruct") is False

    def test_empty_string_returns_false(self):
        assert is_reasoning_model("") is False

    def test_random_string_returns_false(self):
        assert is_reasoning_model("random/model-name") is False
        assert is_reasoning_model("openai/gpt-4o") is False

    def test_no_vendor_prefix_non_matching(self):
        assert is_reasoning_model("some-random-model") is False


class TestGetReasoningEffort:
    def test_deepseek_high_effort(self):
        assert get_reasoning_effort("deepseek-ai/deepseek-v4-flash") == "high"
        assert get_reasoning_effort("deepseek-ai/deepseek-v4-pro") == "high"
        assert get_reasoning_effort("vendor/deepseek-v4-any") == "high"

    def test_glm_medium_effort(self):
        assert get_reasoning_effort("z-ai/glm-5.1") == "medium"
        assert get_reasoning_effort("z-ai/glm4.7") == "medium"
        assert get_reasoning_effort("vendor/glm-anything") == "medium"

    def test_default_high_effort(self):
        assert get_reasoning_effort("other/reasoning-model") == "high"
        assert get_reasoning_effort("random/model") == "high"

    def test_effort_case_insensitive(self):
        assert get_reasoning_effort("DEEPSEEK-AI/DEEPSEEK-V4") == "high"
        assert get_reasoning_effort("Z-AI/GLM-5") == "medium"


class TestConstants:
    def test_reasoning_models_set_not_empty(self):
        assert len(REASONING_MODELS) > 0
        assert "deepseek-ai/deepseek-v4-flash" in REASONING_MODELS
        assert "z-ai/glm-5.1" in REASONING_MODELS

    def test_reasoning_patterns_list_not_empty(self):
        assert len(REASONING_MODEL_PATTERNS) > 0
        assert "deepseek-v4" in REASONING_MODEL_PATTERNS
        assert "glm-5." in REASONING_MODEL_PATTERNS
