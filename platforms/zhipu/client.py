"""
智谱 API 客户端
"""

import os
import httpx
from typing import AsyncIterator, List
from openai import OpenAI

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.models import ModelInfo, ChatMessage
from platforms.base.base_client import BasePlatformClient


class ZhipuClient(BasePlatformClient):
    """智谱 AI API 客户端"""

    platform_name = "zhipu"

    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4"):
        super().__init__(api_key=api_key, base_url=base_url)

        self._client: OpenAI = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(verify=True, timeout=60)
            )
        return self._client

    def chat(self, model: str, messages: List[ChatMessage], **kwargs) -> str:
        """发送聊天请求"""
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        params = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": kwargs.get("max_tokens", 256),
            "temperature": kwargs.get("temperature", 0.7),
        }

        if kwargs.get("thinking") is not None:
            params["thinking"] = kwargs["thinking"]

        completion = self.client.chat.completions.create(**params)

        message = completion.choices[0].message
        response = message.content
        if response is None and hasattr(message, 'reasoning_content'):
            response = message.reasoning_content

        return response or ""

    async def chat_stream(self, model: str, messages: List[ChatMessage], **kwargs) -> AsyncIterator[str]:
        """流式聊天（异步迭代器）"""
        raise NotImplementedError("ZhipuClient 暂不支持流式聊天")

    def list_models(self) -> List[ModelInfo]:
        """获取可用模型列表 - 动态从 API 获取"""
        models = self.client.models.list()
        return [
            ModelInfo(
                id=m.id,
                name=m.id,
                vendor="zhipu",
                is_free_endpoint=True,
                is_available=True,
            )
            for m in models.data
        ]

    def test_connection(self) -> bool:
        """测试 API 连接是否正常"""
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
