"""
通用 OpenAI 兼容客户端

适用于所有兼容 OpenAI API 格式的平台（如 Kimi、MiniMax 等）
"""

import time
from typing import AsyncIterator, List, Optional
import httpx
from openai import OpenAI

from src.models import ModelInfo, ChatMessage
from platforms.base.base_client import BasePlatformClient

class OpenAICompatibleClient(BasePlatformClient):
    """通用 OpenAI 兼容客户端"""

    platform_name = "openai_compatible"

    def __init__(self, api_key: str, base_url: str, platform_name: str = "openai_compatible", **kwargs):
        self.platform_name = platform_name
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
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
        raise NotImplementedError("OpenAICompatibleClient 暂不支持流式聊天")

    def list_models(self) -> List[ModelInfo]:
        """获取可用模型列表 - 动态从 API 获取"""
        try:
            models = self.client.models.list()
            return [
                ModelInfo(
                    id=m.id,
                    name=m.id,
                    vendor=self.platform_name,
                    is_free_endpoint=True,
                    is_available=True,
                )
                for m in models.data
            ]
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []

    def test_connection(self) -> bool:
        """测试 API 连接是否正常"""
        try:
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception as e:
            print(f"连接测试失败: {e}")
            return False

    def close(self):
        """关闭客户端"""
        if self._client:
            self._client.close()
            self._client = None

class AnthropicCompatibleClient(BasePlatformClient):
    """Anthropic Messages API 兼容客户端

    适用于使用 Anthropic Messages API 格式的平台（如 Kimi Code）。
    端点示例: https://api.kimi.com/coding/
    认证: x-api-key header (非 Bearer)
    协议: Anthropic Messages API 兼容
    """

    platform_name = "anthropic_compatible"

    def __init__(self, api_key: str, base_url: str, platform_name: str = "anthropic_compatible", **kwargs):
        self.platform_name = platform_name
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._http_client = None

    @property
    def http_client(self):
        if self._http_client is None:
            import httpx
            self._http_client = httpx.Client(verify=True, timeout=60)
        return self._http_client

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

    def chat(self, model: str, messages: List[ChatMessage], **kwargs) -> str:
        anthropic_messages = []
        system_content = None
        for m in messages:
            if m.role == "system":
                system_content = m.content
                continue
            anthropic_messages.append({"role": m.role, "content": m.content})

        body = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 256),
        }
        if system_content:
            body["system"] = system_content
        if kwargs.get("thinking") is not None:
            body["thinking"] = kwargs["thinking"]

        resp = self.http_client.post(
            f"{self.base_url}v1/messages",
            json=body,
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        for c in data.get("content", []):
            if c.get("type") == "text":
                return c["text"]
        return ""

    async def chat_stream(self, model: str, messages: List[ChatMessage], **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError("AnthropicCompatibleClient 暂不支持流式聊天")

    def list_models(self) -> List[ModelInfo]:
        try:
            resp = self.http_client.get(
                f"{self.base_url}v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            return [
                ModelInfo(
                    id=m["id"],
                    name=m.get("display_name", m["id"]),
                    vendor=self.platform_name,
                    is_free_endpoint=True,
                    is_available=True,
                )
                for m in models
            ]
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []

    def test_connection(self) -> bool:
        try:
            resp = self.http_client.get(
                f"{self.base_url}v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"连接测试失败: {e}")
            return False

    def close(self):
        if self._http_client:
            self._http_client.close()
            self._http_client = None

# 向后兼容别名
KimiClient = AnthropicCompatibleClient

class MiniMaxClient(OpenAICompatibleClient):
    """MiniMax 客户端"""

    def __init__(self, api_key: str, base_url: str = "https://api.minimax.chat/v1", **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, platform_name="minimax", **kwargs)
