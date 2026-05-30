"""
智谱 API 客户端
继承 OpenAICompatibleClient，消除重复代码
"""

from platforms.common.openai_compatible_client import OpenAICompatibleClient
from src.platform_registry import register_platform


class ZhipuClient(OpenAICompatibleClient):
    """智谱 AI API 客户端"""

    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4", **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, platform_name="zhipu", **kwargs)


# 注册平台
ZhipuClient = register_platform(
    name="zhipu",
    display_name="智谱 GLM",
    client_class=ZhipuClient,
    default_base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key_env="ZHIPU_API_KEY",  # pragma: allowlist secret
    description="智谱 AI GLM 系列大模型 API",
    website="https://open.bigmodel.cn"
)(ZhipuClient)
