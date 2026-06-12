"""ModelClassifier 统一分类器测试"""

import pytest
from src.model_classifier import ModelClassifier
from src.models import ModelType


@pytest.fixture
def classifier():
    return ModelClassifier("nvidia")


class TestClassifyByKeywords:
    """按 model_id 关键词分类"""

    def test_image_model_flux(self, classifier):
        assert classifier.classify("black-forest-labs/flux.1-dev") == ModelType.IMAGE_GENERATION

    def test_image_model_stable_diffusion(self, classifier):
        assert classifier.classify("stabilityai/stable-diffusion-xl") == ModelType.IMAGE_GENERATION

    def test_multimodal_model(self, classifier):
        assert classifier.classify("meta/llama-4-maverick") == ModelType.MULTIMODAL

    def test_multimodal_qwen(self, classifier):
        assert classifier.classify("qwen/qwen2.5-vl-72b") == ModelType.MULTIMODAL

    def test_speech_whisper(self, classifier):
        assert classifier.classify("openai/whisper-large-v3") == ModelType.SPEECH

    def test_embedding_nv_embed(self, classifier):
        assert classifier.classify("nvidia/nv-embed-v2") == ModelType.EMBEDDING

    def test_embedding_nemotron_asr(self, classifier):
        """asr 在 speech_keywords 中，优先级高于 non_text_keywords"""
        assert classifier.classify("nvidia/nemotron-asr") == ModelType.SPEECH

    def test_text_model_default(self, classifier):
        assert classifier.classify("meta/llama-3.3-70b-instruct") == ModelType.TEXT

    def test_text_model_deepseek(self, classifier):
        assert classifier.classify("deepseek-ai/deepseek-v4-flash") == ModelType.TEXT


class TestClassifyByCategory:
    """按 category 标签分类（优先级高于关键词）"""

    def test_category_image_generation(self, classifier):
        assert classifier.classify("some-model", category="image-generation") == ModelType.IMAGE_GENERATION

    def test_category_text_to_image(self, classifier):
        assert classifier.classify("some-model", category="text-to-image") == ModelType.IMAGE_GENERATION

    def test_category_multimodal(self, classifier):
        assert classifier.classify("some-model", category="vision-language") == ModelType.MULTIMODAL

    def test_category_speech(self, classifier):
        assert classifier.classify("some-model", category="asr") == ModelType.SPEECH

    def test_category_text(self, classifier):
        assert classifier.classify("some-model", category="text-generation") == ModelType.TEXT

    def test_category_embedding(self, classifier):
        assert classifier.classify("some-model", category="embedding") == ModelType.EMBEDDING

    def test_category_image_editing(self, classifier):
        """'image editing'（空格）不在 image_model_categories 集合中，走 substring 检查"""
        assert classifier.classify("some-model", category="image editing") == ModelType.IMAGE_EDITING

    def test_category_image_editing_hyphen(self, classifier):
        """'image-editing'（连字符）在 image_model_categories 集合中，优先匹配为 IMAGE_GENERATION"""
        assert classifier.classify("some-model", category="image-editing") == ModelType.IMAGE_GENERATION

    def test_category_unknown_fallback_to_keywords(self, classifier):
        """未知 category 应回退到关键词匹配"""
        assert classifier.classify("openai/whisper-large-v3", category="unknown-category") == ModelType.SPEECH


class TestCategoryOverridesKeywords:
    """category 优先级高于关键词"""

    def test_category_text_overrides_image_keyword(self, classifier):
        """即使 model_id 含 image 关键词，category=text 时仍返回 TEXT"""
        assert classifier.classify("flux/some-model", category="text-generation") == ModelType.TEXT

    def test_category_embedding_overrides_text_keyword(self, classifier):
        """即使 model_id 看起来像 text，category=embedding 时返回 EMBEDDING"""
        assert classifier.classify("meta/llama-3.3", category="embedding") == ModelType.EMBEDDING


class TestEdgeCases:
    """边界情况"""

    def test_empty_model_id(self, classifier):
        assert classifier.classify("") == ModelType.TEXT

    def test_no_category(self, classifier):
        assert classifier.classify("meta/llama-3.3", category=None) == ModelType.TEXT

    def test_empty_category(self, classifier):
        """空字符串 category 应该跳过，回退到关键词"""
        assert classifier.classify("meta/llama-3.3", category="") == ModelType.TEXT

    def test_category_case_insensitive(self, classifier):
        assert classifier.classify("some-model", category="IMAGE-GENERATION") == ModelType.IMAGE_GENERATION
