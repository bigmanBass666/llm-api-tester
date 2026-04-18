"""
统一数据结构
所有平台共用相同的数据结构
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    vendor: str
    rank: int = 0
    is_downloadable: bool = False
    is_free_endpoint: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'vendor': self.vendor,
            'rank': self.rank,
            'is_downloadable': self.is_downloadable,
            'is_free_endpoint': self.is_free_endpoint,
            'tags': self.tags
        }


@dataclass
class TestResult:
    """单个模型的测试结果"""
    model_id: str
    rank: int
    status: str
    response_time: float = 0
    error_message: str = ""
    response_preview: str = ""
    is_downloadable: bool = False
    is_free_endpoint: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'model_id': self.model_id,
            'rank': self.rank,
            'status': self.status,
            'response_time': self.response_time,
            'error_message': self.error_message,
            'response_preview': self.response_preview,
            'is_downloadable': self.is_downloadable,
            'is_free_endpoint': self.is_free_endpoint,
            'tags': self.tags
        }


@dataclass
class TestReport:
    """测试报告"""
    timestamp: str
    platform: str
    total: int
    success: int
    failed: int
    timeout: int
    results: List[TestResult]

    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'platform': self.platform,
            'total': self.total,
            'success': self.success,
            'failed': self.failed,
            'timeout': self.timeout,
            'results': [r.to_dict() for r in self.results]
        }


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str

    def to_dict(self) -> dict:
        return {'role': self.role, 'content': self.content}