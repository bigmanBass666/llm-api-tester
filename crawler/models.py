"""
NVIDIA 模型数据结构 — crawler 层内部使用
"""

from dataclasses import dataclass
from typing import List

from src.models import ModelInfo, TestResult


class _DefaultResult:
    """用于 ModelStore 中无结果时的默认值"""
    status = "pending"
    response_time = 0.0
    error_message = ""


class ModelStore:
    """模型数据存储 — models 存储身份信息，results 存储测试结果"""

    def __init__(self):
        self.models: List[ModelInfo] = []
        self.results: dict = {}

    def add_model(self, model: ModelInfo):
        if not any(m.id == model.id for m in self.models):
            self.models.append(model)

    def add_models(self, models: List[ModelInfo]):
        for m in models:
            self.add_model(m)

    def set_results(self, results: list):
        self.results = {r.model_id: r for r in results}

    def get_by_rank(self, start: int, end: int) -> List[ModelInfo]:
        return [m for m in self.models if start <= m.rank <= end]

    def get_by_vendor(self, vendor: str) -> List[ModelInfo]:
        return [m for m in self.models if m.vendor == vendor]

    def _result(self, m: ModelInfo):
        return self.results.get(m.id, _DefaultResult())

    def get_available(self) -> List[ModelInfo]:
        return [m for m in self.models if m.is_available and m.id not in self.results]

    def get_successful(self) -> List[ModelInfo]:
        return [m for m in self.models if self._result(m).status == "success"]

    def get_failed(self) -> List[ModelInfo]:
        return [m for m in self.models if self._result(m).status in ("failed", "timeout")]

    def summary(self) -> dict:
        return {
            "total": len(self.models),
            "success": sum(1 for r in self.results.values() if r.status == "success"),
            "failed": sum(1 for r in self.results.values() if r.status == "failed"),
            "timeout": sum(1 for r in self.results.values() if r.status == "timeout"),
            "pending": sum(1 for m in self.models if m.id not in self.results),
            "testing": 0,
        }

    def to_list(self) -> List[dict]:
        return [
            {
                "rank": m.rank,
                "id": m.id,
                "vendor": m.vendor,
                "status": self._result(m).status,
                "response_time": self._result(m).response_time,
                "is_downloadable": m.is_downloadable,
                "is_free_endpoint": m.is_free_endpoint,
                "tags": m.tags or [],
                "category": m.category,
                "is_text_model": m.is_text_model,
                "is_callable": self._result(m).status == "success",
                "error": self._result(m).error_message[:100] if self._result(m).error_message else None,
            }
            for m in sorted(self.models, key=lambda x: x.rank)
        ]
