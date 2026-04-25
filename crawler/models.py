"""
NVIDIA 模型数据结构
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class ModelInfo:
    """NVIDIA 模型信息"""
    id: str                          # 模型ID (如 qwen/qwen3-coder-480b-a35b-instruct)
    name: str                        # 显示名称
    vendor: str                      # 供应商 (如 qwen, google, meta)
    rank: int = 0                    # 热度排名
    is_available: bool = True        # 是否可用
    is_reasoning: bool = False       # 是否推理模型
    reasoning_effort: Optional[str] = None  # 推理努力程度 (low, medium, high)
    test_status: str = "pending"     # pending / testing / success / failed / timeout
    response_time: float = 0         # 响应时间(秒)
    error_message: str = ""          # 错误信息
    test_date: Optional[str] = None  # 测试时间
    token_usage: int = 0             # Token使用量
    is_downloadable: bool = False    # 是否可下载
    is_free_endpoint: bool = True    # 是否有免费端点（大多数NVIDIA模型都是免费的）
    tags: List[str] = None          # 其他标签（context window, use case 等）
    description: Optional[str] = None  # 模型描述文本
    category: Optional[str] = None   # 模型分类标签（如 text-generation, embedding）
    is_text_model: bool = True       # 是否为文字模型（默认 True）

    @property
    def status_icon(self) -> str:
        """状态图标"""
        icons = {
            "pending": "⏳",
            "testing": "🔄",
            "success": "✅",
            "failed": "❌",
            "timeout": "⏰",
        }
        return icons.get(self.test_status, "❓")


# 预定义推理模型列表
REASONING_MODELS = {
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "z-ai/glm-5.1",
    "z-ai/glm-4.7",
}

# 推理模型 ID 模式（用于动态匹配）
REASONING_MODEL_PATTERNS = [
    "deepseek-v4",
    "glm-5.",
    "glm-4.7",
    "reasoning",
    "thinking",
]


def is_reasoning_model(model_id: str) -> bool:
    """
    判断模型是否为推理模型

    Args:
        model_id: 模型 ID (如 deepseek-ai/deepseek-v4-flash)

    Returns:
        bool: 是否为推理模型
    """
    if not model_id:
        return False

    model_id_lower = model_id.lower()

    # 检查是否在预定义列表中
    if model_id in REASONING_MODELS:
        return True

    # 检查 ID 部分（去掉 vendor 前缀）
    id_part = model_id.split("/")[-1].lower() if "/" in model_id else model_id.lower()

    # 检查是否匹配推理模型模式
    for pattern in REASONING_MODEL_PATTERNS:
        if pattern.lower() in id_part:
            return True

    return False


def get_reasoning_effort(model_id: str) -> str:
    """
    获取推理模型的推理努力程度

    Args:
        model_id: 模型 ID

    Returns:
        str: 推理努力程度 (low, medium, high)
    """
    # DeepSeek V4 系列默认 high
    if "deepseek-v4" in model_id.lower():
        return "high"

    # GLM 系列默认 medium
    if "glm" in model_id.lower():
        return "medium"

    return "high"  # 默认值


@dataclass
class TestReport:
    """测试报告"""
    timestamp: str
    total_models: int
    successful: int
    failed: int
    timeout: int
    pending: int
    models: List[ModelInfo]
    duration: float = 0  # 总测试时长(秒)


class ModelStore:
    """模型数据存储"""

    def __init__(self):
        self.models: List[ModelInfo] = []

    def add_model(self, model: ModelInfo):
        """添加模型"""
        # 避免重复
        if not any(m.id == model.id for m in self.models):
            self.models.append(model)

    def add_models(self, models: List[ModelInfo]):
        """批量添加模型"""
        for m in models:
            self.add_model(m)

    def get_by_rank(self, start: int, end: int) -> List[ModelInfo]:
        """按排名范围获取模型"""
        return [m for m in self.models if start <= m.rank <= end]

    def get_by_vendor(self, vendor: str) -> List[ModelInfo]:
        """按供应商获取模型"""
        return [m for m in self.models if m.vendor == vendor]

    def get_available(self) -> List[ModelInfo]:
        """获取可测试的模型"""
        return [m for m in self.models if m.is_available and m.test_status == "pending"]

    def get_successful(self) -> List[ModelInfo]:
        """获取测试成功的模型"""
        return [m for m in self.models if m.test_status == "success"]

    def get_failed(self) -> List[ModelInfo]:
        """获取测试失败的模型"""
        return [m for m in self.models if m.test_status in ("failed", "timeout")]

    def summary(self) -> dict:
        """获取统计摘要"""
        return {
            "total": len(self.models),
            "success": sum(1 for m in self.models if m.test_status == "success"),
            "failed": sum(1 for m in self.models if m.test_status == "failed"),
            "timeout": sum(1 for m in self.models if m.test_status == "timeout"),
            "pending": sum(1 for m in self.models if m.test_status == "pending"),
            "testing": sum(1 for m in self.models if m.test_status == "testing"),
        }

    def to_list(self) -> List[dict]:
        """转换为列表格式（包含标签信息）"""
        return [
            {
                "rank": m.rank,
                "id": m.id,
                "vendor": m.vendor,
                "status": m.test_status,
                "response_time": m.response_time,
                "is_downloadable": m.is_downloadable,
                "is_free_endpoint": m.is_free_endpoint,
                "tags": m.tags or [],
                "category": m.category,
                "is_text_model": m.is_text_model,
                "is_callable": m.test_status == "success",  # 是否能被正常调用
                "error": m.error_message[:100] if m.error_message else None,
            }
            for m in sorted(self.models, key=lambda x: x.rank)
        ]