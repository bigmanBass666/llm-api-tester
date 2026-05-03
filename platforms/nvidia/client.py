"""
NVIDIA NIM API 客户端
调用 https://integrate.api.nvidia.com/v1
"""

import os
from typing import Optional, List, Iterator

import httpx
from openai import OpenAI

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.models import ModelInfo, ChatMessage
from platforms.base.base_client import BasePlatformClient
from src.platform_registry import register_platform


class NvidiaClient(BasePlatformClient):
    """NVIDIA NIM API 客户端"""

    platform_name = "nvidia"
    platform_display_name = "NVIDIA NIM"

    FREE_MODELS = {
        "qwen3-coder": "qwen/qwen3-coder-480b-a35b-instruct",
        "minimax-m2.7": "minimaxai/minimax-m2.7",
        "deepseek-v31": "deepseek-ai/deepseek-v3.1-terminus",
        "llama4-maverick": "meta/llama-4-maverick-17b-128e-instruct",
        "kimi-k2": "moonshotai/kimi-k2-instruct-0905",
        "gemma-7b": "google/gemma-7b",
        "phi3-mini": "microsoft/phi-3-mini-128k-instruct",
        "step-3.5-flash": "stepfun-ai/step-3.5-flash",
        "glm-4.7": "z-ai/glm4.7",
    }

    def __init__(self, api_key: str = None, base_url: Optional[str] = None, **kwargs):
        # 不再需要手动调用 SSL 设置，基类会自动处理
        self._client: Optional[OpenAI] = None
        
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://integrate.api.nvidia.com/v1",
            **kwargs
        )
        
        self.config = kwargs

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(verify=True, timeout=30)
            )
        return self._client

    def chat(
        self,
        model: str,
        messages: List[ChatMessage],
        **kwargs
    ) -> str:
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        completion = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            **kwargs
        )

        response = completion.choices[0].message.content
        if response is None and hasattr(completion.choices[0].message, 'reasoning_content'):
            response = completion.choices[0].message.reasoning_content

        return response or ""

    def chat_stream(
        self,
        model: str,
        messages: List[ChatMessage],
        **kwargs
    ) -> Iterator[str]:
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        completion = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            stream=True,
            **kwargs
        )

        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def list_models(self) -> List[ModelInfo]:
        models = self.client.models.list()
        return [
            ModelInfo(
                id=m.id,
                name=m.id,
                vendor="nvidia",
                is_free_endpoint=True,
                max_tokens=4096,
                context_window=128000,
                description=""
            )
            for m in models.data
        ]

    def test_connection(self) -> bool:
        try:
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception:
            return False

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def quick_chat(self, model_key: str, message: str, **kwargs) -> str:
        if model_key not in self.FREE_MODELS:
            raise ValueError(
                f"未知模型: {model_key}，可用模型: {list(self.FREE_MODELS.keys())}"
            )

        return self.chat(
            self.FREE_MODELS[model_key],
            [ChatMessage(role="user", content=message)],
            **kwargs
        )


# 注册平台（使用装饰器）
NvidiaClient = register_platform(
    name="nvidia",
    display_name="NVIDIA NIM",
    client_class=NvidiaClient,
    default_base_url="https://integrate.api.nvidia.com/v1",
    api_key_env="NVIDIA_API_KEY",
    description="NVIDIA NIM 提供的多种开源大模型 API",
    website="https://build.nvidia.com"
)(NvidiaClient)


def nvidia_chat(model_key: str, message: str, api_key: Optional[str] = None, **kwargs) -> str:
    """快速调用 NVIDIA 模型（便捷函数）"""
    if api_key is None:
        api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("请设置 NVIDIA_API_KEY 环境变量或提供 api_key 参数")

    client = NvidiaClient(api_key=api_key)
    try:
        return client.quick_chat(model_key, message, **kwargs)
    finally:
        client.close()
