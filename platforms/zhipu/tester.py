"""
智谱模型测试器
"""

from platforms.base.base_tester import BaseTester


class ZhipuTester(BaseTester):
    """智谱模型测试器"""

    platform_name = "zhipu"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
