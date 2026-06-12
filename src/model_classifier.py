"""统一模型类型分类器

将分散在 scraper 和 client 中的分类逻辑集中到一处。
配置驱动，按优先级判定：先查 category（如有），再查 model_id 关键词。

用法:
    classifier = ModelClassifier("nvidia")
    model_type = classifier.classify("meta/llama-4-maverick")                     # → MULTIMODAL
    model_type = classifier.classify("nvidia/nv-embed-v2", category="embedding")  # → EMBEDDING
"""

from typing import Optional

from .models import ModelType
from .platform_config import PlatformConfigLoader


class ModelClassifier:
    """配置驱动的模型类型分类器"""

    def __init__(self, platform: str):
        config = PlatformConfigLoader.get_scraper_config(platform)
        if not config:
            raise ValueError(f"未找到平台 {platform} 的爬虫配置")

        self._image_categories = config.image_model_categories
        self._multimodal_categories = config.multimodal_categories
        self._speech_categories = config.speech_categories
        self._text_categories = config.text_model_categories

        self._image_keywords = config.image_model_keywords
        self._multimodal_keywords = config.multimodal_keywords
        self._speech_keywords = config.speech_keywords
        self._non_text_keywords = config.non_text_keywords

    def classify(self, model_id: str, category: str = None) -> ModelType:
        """统一分类入口

        Args:
            model_id: 模型 ID（如 "meta/llama-4-maverick"）
            category: 可选的类别标签（来自网页卡片，如 "image-generation"）

        Returns:
            ModelType 枚举值
        """
        if category:
            result = self._classify_by_category(category)
            if result is not None:
                return result

        return self._classify_by_keywords(model_id)

    def _classify_by_category(self, category: str) -> Optional[ModelType]:
        """按类别标签分类（优先级最高）"""
        cat = category.lower()

        if cat in self._image_categories:
            return ModelType.IMAGE_GENERATION
        if cat in self._multimodal_categories:
            return ModelType.MULTIMODAL
        if cat in self._speech_categories:
            return ModelType.SPEECH
        if cat in self._text_categories:
            return ModelType.TEXT
        if any(kw in cat for kw in ('embedding', 'extraction')):
            return ModelType.EMBEDDING
        if any(kw in cat for kw in ('image-editing', 'image editing')):
            return ModelType.IMAGE_EDITING

        return None  # 无法通过类别判定，回退到关键词

    def _classify_by_keywords(self, model_id: str) -> ModelType:
        """按 model_id 中的关键词分类（回退策略）"""
        mid = model_id.lower()

        for kw in self._image_keywords:
            if kw in mid:
                return ModelType.IMAGE_GENERATION
        for kw in self._multimodal_keywords:
            if kw in mid:
                return ModelType.MULTIMODAL
        for kw in self._speech_keywords:
            if kw in mid:
                return ModelType.SPEECH
        for kw in self._non_text_keywords:
            if kw in mid:
                return ModelType.EMBEDDING

        return ModelType.TEXT


# ── 推理模型识别 ──────────────────────────────────────

# 精确匹配集合
REASONING_MODELS = {
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "z-ai/glm-5.1",
    "z-ai/glm-4.7",
}

# 模糊匹配模式（用于动态匹配 model_id 中的关键词）
REASONING_MODEL_PATTERNS = [
    "deepseek-v4",
    "glm-5.",
    "glm-4.7",
    "reasoning",
    "thinking",
]


def is_reasoning_model(model_id: str) -> bool:
    """判断模型是否为推理模型"""
    if not model_id:
        return False
    if model_id in REASONING_MODELS:
        return True
    id_part = model_id.split("/")[-1].lower() if "/" in model_id else model_id.lower()
    return any(p.lower() in id_part for p in REASONING_MODEL_PATTERNS)


def get_reasoning_effort(model_id: str) -> str:
    """获取推理模型的 effort 级别"""
    mid = model_id.lower()
    if "deepseek-v4" in mid:
        return "high"
    if "glm" in mid:
        return "medium"
    return "high"
