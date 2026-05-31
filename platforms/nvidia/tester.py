"""
NVIDIA 模型测试器
"""

from dataclasses import replace

from src.models import ModelInfo
from platforms.base.base_tester import BaseTester


class NvidiaTester(BaseTester):
    """NVIDIA 模型测试器"""

    platform_name = "nvidia"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://integrate.api.nvidia.com/v1"

    async def test_single(self, model: ModelInfo, timeout=60):
        # 将 NVIDIA 网页 ID (下划线) 转换为 API ID (点号)，不修改入参
        api_model_id = model.id.replace('_', '.') if '_' in model.id else model.id
        if api_model_id != model.id:
            model = replace(model, id=api_model_id)
        return await super().test_single(model, timeout)
