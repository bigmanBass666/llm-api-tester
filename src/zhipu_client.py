"""
智谱AI GLM API 客户端
调用 https://open.bigmodel.cn/api/paas/v4
"""

import os
from typing import Optional, List, Iterator
import time

import httpx
from openai import OpenAI

from .base_client import BaseClient, ChatMessage, ModelInfo
from .platform_registry import register_platform


@register_platform(
    name="zhipu",
    display_name="智谱 GLM",
    client_class=None,  # 稍后设置
    default_base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key_env="ZHIPU_API_KEY",
    description="智谱 AI 的 GLM 系列模型，包含免费API",
    website="https://www.bigmodel.cn/"
)
class ZhipuClient(BaseClient):
    """智谱AI API 客户端"""

    platform_name = "zhipu"
    platform_display_name = "智谱 GLM"

    # 预定义的免费模型
    FREE_MODELS = {
        "glm-4-flash": "glm-4-flash-250414",
        "glm-4v-flash": "glm-4v-flash",
        "glm-4.7-flash": "glm-4.7-flash",
        "glm-4.1v-thinking-flash": "glm-4.1v-thinking-flash",
        "cogview-3-flash": "cogview-3-flash",
        "cogvideox-flash": "cogvideox-flash",
        "glm-4.6v-flash": "glm-4.6v-flash",
    }

    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        # 设置 SSL 证书
        os.environ.setdefault(
            'SSL_CERT_FILE',
            r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem'
        )
        os.environ.setdefault(
            'REQUESTS_CA_BUNDLE',
            r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem'
        )

        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://open.bigmodel.cn/api/paas/v4",
            **kwargs
        )

        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(verify=False, timeout=60)
            )
        return self._client

    def chat(
        self,
        model: str,
        messages: List[ChatMessage],
        **kwargs
    ) -> str:
        """发送聊天请求"""
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        # 默认参数
        params = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": kwargs.get("max_tokens", 256),
            "temperature": kwargs.get("temperature", 0.7),
        }

        # 支持模型特定的参数
        if kwargs.get("thinking") is not None:
            # 某些模型支持 thinking 参数（如 glm-4.7-flash, glm-4.1v-thinking-flash）
            params["thinking"] = kwargs["thinking"]

        completion = self.client.chat.completions.create(**params)

        # 智谱模型可能返回 reasoning_content 或 content
        message = completion.choices[0].message
        response = message.content
        if response is None and hasattr(message, 'reasoning_content'):
            response = message.reasoning_content

        return response or ""

    def chat_stream(
        self,
        model: str,
        messages: List[ChatMessage],
        **kwargs
    ) -> Iterator[str]:
        """流式聊天请求"""
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        params = {
            "model": model,
            "messages": openai_messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 256),
            "temperature": kwargs.get("temperature", 0.7),
        }

        if kwargs.get("thinking") is not None:
            params["thinking"] = kwargs["thinking"]

        completion = self.client.chat.completions.create(**params)

        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def list_models(self) -> List[ModelInfo]:
        """获取可用模型列表"""
        models = []
        for key, model_id in self.FREE_MODELS.items():
            models.append(ModelInfo(
                id=model_id,
                name=key,
                platform=self.platform_name,
                is_free=True,
                description=f"智谱AI {key}"
            ))
        return models

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception:
            return False

    def close(self):
        """关闭客户端"""
        if self._client:
            self._client.close()
            self._client = None

    def quick_chat(self, model_key: str, message: str, **kwargs) -> str:
        """
        快速聊天（使用预定义模型名称）

        Args:
            model_key: 模型键名，如 "glm-4-flash"
            message: 用户消息
            **kwargs: 其他参数

        Returns:
            模型回复
        """
        if model_key not in self.FREE_MODELS:
            raise ValueError(
                f"未知模型: {model_key}，可用模型: {list(self.FREE_MODELS.keys())}"
            )

        return self.chat(
            self.FREE_MODELS[model_key],
            [ChatMessage(role="user", content=message)],
            **kwargs
        )


# 便捷函数
def zhipu_chat(model_key: str, message: str, api_key: Optional[str] = None, **kwargs) -> str:
    """
    快速调用智谱AI模型

    Args:
        model_key: 模型键名，如 "glm-4-flash"
        message: 用户消息
        api_key: API 密钥（可选）
        **kwargs: 其他参数

    Returns:
        模型回复
    """
    if api_key is None:
        api_key = os.environ.get("ZHIPU_API_KEY")

    if not api_key:
        raise ValueError("未提供API Key，请设置ZHIPU_API_KEY环境变量或提供api_key参数")

    client = ZhipuClient(api_key=api_key)
    try:
        return client.quick_chat(model_key, message, **kwargs)
    finally:
        client.close()
