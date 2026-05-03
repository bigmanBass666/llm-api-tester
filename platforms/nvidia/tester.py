"""
NVIDIA 模型测试器
"""

from platforms.base.base_tester import BaseTester


class NvidiaTester(BaseTester):
    """NVIDIA 模型测试器"""

    platform_name = "nvidia"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://integrate.api.nvidia.com/v1"

    async def test_single(self, model, timeout=60):
        api_model_id = model.id.replace('_', '.') if '_' in model.id else model.id
        original_id = model.id
        model.id = api_model_id
        result = await super().test_single(model, timeout)
        model.id = original_id
        result.model_id = original_id
        return result
