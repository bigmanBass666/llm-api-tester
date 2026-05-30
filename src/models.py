"""统一数据模型层 - 全域唯一的数据结构定义

所有模块（src/, platforms/, crawler/）均应从此处 import 数据类。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from enum import Enum


class TestStatus(str, Enum):
    PENDING = "pending"
    TESTING = "testing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ReasoningEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelType(str, Enum):
    TEXT = "text"
    IMAGE_GENERATION = "image_generation"
    IMAGE_EDITING = "image_editing"
    EMBEDDING = "embedding"
    MULTIMODAL = "multimodal"
    SPEECH = "speech"


@dataclass
class ChatMessage:
    """统一的消息格式"""
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ScrapedMetadata:
    """爬虫采集的元数据 — 从 ModelInfo/TestResult 分离出来的独立关注点

    Phase 1: 新增数据结构
    Phase 4b: 将成为 ModelInfo 和 TestResult 中爬虫元数据的唯一载体
    """

    call_volume: str = ""
    published_at: Optional[str] = None
    deprecation_info: Optional[str] = None
    endpoint_type: str = "unknown"
    inference_provider: Optional[str] = None
    created_at: Optional[int] = None
    api_owned_by: Optional[str] = None
    is_hosted: Optional[bool] = None

    def to_dict(self) -> dict:
        return {
            "call_volume": self.call_volume,
            "published_at": self.published_at,
            "deprecation_info": self.deprecation_info,
            "endpoint_type": self.endpoint_type,
            "inference_provider": self.inference_provider,
            "created_at": self.created_at,
            "api_owned_by": self.api_owned_by,
            "is_hosted": self.is_hosted,
        }


@dataclass
class ModelInfo:
    """全域统一的模型信息 — 合并了所有版本的字段"""

    id: str
    name: str
    model_type: ModelType = ModelType.TEXT
    vendor: str = ""
    rank: int = 0
    category: Optional[str] = None
    is_free_endpoint: bool = True
    is_downloadable: bool = False
    is_available: bool = True
    is_reasoning: bool = False
    max_tokens: int = 4096
    context_window: int = 128000
    description: str = ""
    test_status: str = "pending"
    response_time: float = 0.0
    error_message: str = ""
    token_usage: int = 0
    test_date: Optional[str] = None
    reasoning_effort: Optional[str] = None
    tags: Optional[List[str]] = None
    href: str = ""
    call_volume: str = ""
    published_at: Optional[str] = None
    deprecation_info: Optional[str] = None
    endpoint_type: str = "unknown"
    inference_provider: Optional[str] = None
    created_at: Optional[int] = None
    api_owned_by: Optional[str] = None
    is_hosted: Optional[bool] = None

    @property
    def scraped(self) -> Optional['ScrapedMetadata']:
        """桥接属性：从顶层字段构造 ScrapedMetadata（Phase 4b 后改为正式字段）"""
        has_any = any([
            self.call_volume, self.published_at, self.deprecation_info,
            self.endpoint_type != "unknown", self.inference_provider,
            self.created_at, self.api_owned_by, self.is_hosted is not None,
        ])
        if not has_any:
            return None
        return ScrapedMetadata(
            call_volume=self.call_volume,
            published_at=self.published_at,
            deprecation_info=self.deprecation_info,
            endpoint_type=self.endpoint_type,
            inference_provider=self.inference_provider,
            created_at=self.created_at,
            api_owned_by=self.api_owned_by,
            is_hosted=self.is_hosted,
        )

    @property
    def status_icon(self) -> str:
        icons = {
            "pending": "⏳", "testing": "\U0001f504",
            "success": "✅", "failed": "❌", "timeout": "⏰",
        }
        return icons.get(self.test_status, "❓")

    @property
    def is_callable(self) -> bool:
        return self.test_status == "success"

    @property
    def is_text_model(self) -> bool:
        return self.model_type == ModelType.TEXT

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "rank": self.rank,
            "test_status": self.test_status,
            "response_time": round(self.response_time, 2),
            "is_downloadable": self.is_downloadable,
            "is_free_endpoint": self.is_free_endpoint,
            "tags": self.tags or [],
            "category": self.category,
            "is_text_model": self.is_text_model,
            "is_callable": self.is_callable,
            "call_volume": self.call_volume,
            "published_at": self.published_at,
            "deprecation_info": self.deprecation_info,
            "endpoint_type": self.endpoint_type,
            "inference_provider": self.inference_provider,
            "created_at": self.created_at,
            "api_owned_by": self.api_owned_by,
            "error": self.error_message[:200] if self.error_message else "",
        }


@dataclass
class TestResult:
    """独立的测试结果 — 从 ModelInfo 分离测试状态"""
    model_id: str
    model_type: str = "text"
    rank: int = 0
    status: str = "pending"
    response_time: float = 0.0
    error_message: str = ""
    response_preview: str = ""
    is_downloadable: bool = False
    is_free_endpoint: bool = True
    tags: Optional[List[str]] = None
    reasoning_content: str = ""
    token_usage: int = 0
    call_volume: str = ""
    published_at: Optional[str] = None
    deprecation_info: Optional[str] = None
    endpoint_type: str = "unknown"
    inference_provider: Optional[str] = None
    created_at: Optional[int] = None
    api_owned_by: Optional[str] = None
    is_hosted: Optional[bool] = None
    scraped: Optional[ScrapedMetadata] = None

    @classmethod
    def from_model_info(cls, model: 'ModelInfo', **test_fields) -> 'TestResult':
        """从 ModelInfo + 测试字段构造 TestResult（替代 _model_to_result_kwargs）"""
        scraped = model.scraped
        return cls(
            model_id=model.id,
            model_type=model.model_type.value,
            rank=model.rank,
            is_downloadable=model.is_downloadable,
            is_free_endpoint=model.is_free_endpoint,
            tags=model.tags,
            call_volume=model.call_volume,
            published_at=model.published_at,
            deprecation_info=model.deprecation_info,
            endpoint_type=model.endpoint_type,
            inference_provider=model.inference_provider,
            created_at=model.created_at,
            api_owned_by=model.api_owned_by,
            is_hosted=model.is_hosted,
            scraped=scraped,
            **test_fields,
        )

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "rank": self.rank,
            "status": self.status,
            "response_time": round(self.response_time, 2),
            "error_message": self.error_message[:200] if self.error_message else "",
            "response_preview": self.response_preview[:100] if self.response_preview else "",
            "is_downloadable": self.is_downloadable,
            "is_free_endpoint": self.is_free_endpoint,
            "tags": self.tags or [],
            "token_usage": self.token_usage,
            "call_volume": self.call_volume,
            "published_at": self.published_at,
            "deprecation_info": self.deprecation_info,
            "endpoint_type": self.endpoint_type,
            "inference_provider": self.inference_provider,
            "created_at": self.created_at,
            "api_owned_by": self.api_owned_by,
        }


@dataclass
class TestReport:
    """测试报告汇总"""
    timestamp: str
    platform: str = "nvidia"
    total: int = 0
    success: int = 0
    failed: int = 0
    timeout: int = 0
    pending: int = 0
    duration: float = 0.0
    results: Optional[List[Any]] = None

    def to_dict(self) -> dict:
        result_data = []
        if self.results:
            for r in self.results:
                if hasattr(r, 'to_dict'):
                    result_data.append(r.to_dict())
                else:
                    result_data.append(r)

        return {
            "timestamp": self.timestamp,
            "platform": self.platform,
            "statistics": {
                "total_models": self.total,
                "successful": self.success,
                "failed": self.failed,
                "timeout": self.timeout,
                "pending": self.pending,
                "success_rate": f"{self.success/self.total*100:.1f}%" if self.total > 0 else "N/A",
            },
            "duration_seconds": round(self.duration, 2),
            "results": result_data,
        }
