"""统一数据模型层 - 全域唯一的数据结构定义

所有模块（src/, platforms/, crawler/）均应从此处 import 数据类。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
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


@dataclass
class ChatMessage:
    """统一的消息格式"""
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ModelInfo:
    """全域统一的模型信息 - 合并了所有版本的字段"""

    id: str
    name: str
    vendor: str = ""
    rank: int = 0
    category: Optional[str] = None
    is_text_model: bool = True
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

    @property
    def status_icon(self) -> str:
        icons = {
            "pending": "\u23f3", "testing": "\U0001f504",
            "success": "\u2705", "failed": "\u274c", "timeout": "\u23f0",
        }
        return icons.get(self.test_status, "\u2753")

    @property
    def is_callable(self) -> bool:
        return self.test_status == "success"

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
            "error": self.error_message[:200] if self.error_message else "",
        }


@dataclass
class TestResult:
    """独立的测试结果 — 从 ModelInfo 分离测试状态"""
    model_id: str
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

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "rank": self.rank,
            "status": self.status,
            "response_time": round(self.response_time, 2),
            "error_message": self.error_message[:200] if self.error_message else "",
            "response_preview": self.response_preview[:100] if self.response_preview else "",
            "is_downloadable": self.is_downloadable,
            "is_free_endpoint": self.is_free_endpoint,
            "tags": self.tags or [],
            "token_usage": self.token_usage,
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
