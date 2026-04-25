"""
NVIDIA NIM API 客户端
调用 https://integrate.api.nvidia.com/v1
"""

import os
from typing import Optional, List, Iterator

import httpx
from openai import OpenAI

from .base_client import BaseClient, ChatMessage, ModelInfo
from .platform_registry import register_platform


@register_platform(
    name="nvidia",
    display_name="NVIDIA NIM",
    client_class=None,  # 稍后设置
    default_base_url="https://integrate.api.nvidia.com/v1",
    api_key_env="NVIDIA_API_KEY",
    description="NVIDIA NIM 提供的多种开源大模型 API",
    website="https://build.nvidia.com"
)
class NvidiaClient(BaseClient):
    """NVIDIA NIM API 客户端"""

    platform_name = "nvidia"
    platform_display_name = "NVIDIA NIM"

    # 预定义的免费模型（测试过可用的）
    FREE_MODELS = {
        # 简短名称 -> 完整模型 ID
        "qwen3-coder": "qwen/qwen3-coder-480b-a35b-instruct",
        "minimax-m2.7": "minimaxai/minimax-m2.7",
        "deepseek-v31": "deepseek-ai/deepseek-v3.1-terminus",
        "llama4-maverick": "meta/llama-4-maverick-17b-128e-instruct",
        "kimi-k2": "moonshotai/kimi-k2-instruct-0905",
        "gemma-7b": "google/gemma-7b",
        "phi3-mini": "microsoft/phi-3-mini-128k-instruct",
        "step-3.5-flash": "stepfun-ai/step-3.5-flash",
        "glm-4.7": "z-ai/glm4.7",
    # "glm5": "z-ai/glm5",  # ❌ 模型不响应（2026-04-14 测试：chat completions 超时无响应）
    }

    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        from .ssl_config import setup_ssl_certificates
        setup_ssl_certificates()

        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://integrate.api.nvidia.com/v1",
            **kwargs
        )

        self._client: Optional[OpenAI] = None

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
        """发送聊天请求"""
        # 转换消息格式
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        completion = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            **kwargs
        )

        # 某些模型（如 GLM、Step）可能只返回 reasoning_content
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
        """流式聊天请求"""
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
        """获取可用模型列表"""
        models = self.client.models.list()
        return [
            ModelInfo(
                id=m.id,
                name=m.id,
                platform=self.platform_name,
                description=""
            )
            for m in models.data
        ]

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
            model_key: 模型键名，如 "minimax-m2.7"
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
def nvidia_chat(model_key: str, message: str, api_key: Optional[str] = None, **kwargs) -> str:
    """
    快速调用 NVIDIA 模型

    Args:
        model_key: 模型键名，如 "minimax-m2.7"
        message: 用户消息
        api_key: API 密钥（可选）
        **kwargs: 其他参数

    Returns:
        模型回复
    """
    if api_key is None:
        api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("请设置 NVIDIA_API_KEY 环境变量或提供 api_key 参数")

    client = NvidiaClient(api_key=api_key)
    try:
        return client.quick_chat(model_key, message, **kwargs)
    finally:
        client.close()