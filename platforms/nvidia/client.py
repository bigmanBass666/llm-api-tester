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
from src.platform_config import PlatformConfigLoader


class NvidiaClient(BasePlatformClient):
    """NVIDIA NIM API 客户端"""

    platform_name = "nvidia"
    platform_display_name = "NVIDIA NIM"

    def __init__(self, api_key: str = None, base_url: Optional[str] = None, **kwargs):
        self._client: Optional[OpenAI] = None

        self._load_config()

        super().__init__(
            api_key=api_key,
            base_url=base_url or self._platform_base_url,
            **kwargs
        )

        self.config = kwargs

    def _load_config(self):
        """从配置加载器加载配置"""
        config = PlatformConfigLoader.get_config(self.platform_name)
        if not config:
            raise ValueError(f"未找到 {self.platform_name} 平台的配置，请检查 configs/platforms.yaml")

        self._platform_base_url = config.base_url or "https://integrate.api.nvidia.com/v1"

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

    def generate_image(self, model: str, prompt: str, **kwargs) -> dict:
        import base64
        import requests
        import time

        width = kwargs.get('width', 1024)
        height = kwargs.get('height', 1024)
        seed = kwargs.get('seed', 0)
        steps = kwargs.get('steps')

        invoke_url = f"https://ai.api.nvidia.com/v1/genai/{model}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": seed,
        }
        if steps is not None:
            payload["steps"] = steps

        ttfb = None
        gen_start = time.time()
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=120)

        if response.status_code == 422:
            error_body = response.json()
            details = error_body.get("detail", [])
            fixed = False
            for d in details:
                loc = d.get("loc", [])
                msg = d.get("msg", "")
                if "width" in loc and "should be" in msg:
                    allowed = [int(x.strip()) for x in msg.split("should be")[-1].split("or") if x.strip().isdigit()] if "or" in msg else []
                    if not allowed:
                        nums = [int(x) for x in msg.replace(",", " ").split() if x.isdigit()]
                        allowed = [n for n in nums if n >= 768]
                    if allowed:
                        payload["width"] = min(allowed, key=lambda x: abs(x - width))
                        fixed = True
                if "height" in loc and "should be" in msg:
                    allowed = [int(x.strip()) for x in msg.split("should be")[-1].split("or") if x.strip().isdigit()] if "or" in msg else []
                    if not allowed:
                        nums = [int(x) for x in msg.replace(",", " ").split() if x.isdigit()]
                        allowed = [n for n in nums if n >= 768]
                    if allowed:
                        payload["height"] = min(allowed, key=lambda x: abs(x - height))
                        fixed = True
                if "steps" in loc:
                    payload.pop("steps", None)
                    fixed = True
            if fixed:
                gen_start = time.time()
                response = requests.post(invoke_url, headers=headers, json=payload, timeout=120)

        ttfb = time.time() - gen_start
        response.raise_for_status()

        decode_start = time.time()
        response_body = response.json()
        img_data = response_body['artifacts'][0]['base64']
        img_bytes = base64.b64decode(img_data)
        decode_time = time.time() - decode_start

        actual_w = payload.get("width", width)
        actual_h = payload.get("height", height)
        actual_steps = payload.get("steps")

        return {
            "success": True,
            "image_size_bytes": len(img_bytes),
            "image_dimensions": f"{actual_w}x{actual_h}",
            "generation_steps": actual_steps,
            "ttfb": round(ttfb, 3),
            "decode_time": round(decode_time, 3),
        }

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
