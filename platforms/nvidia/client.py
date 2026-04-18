"""
NVIDIA API 客户端
"""

import os
import httpx
from typing import List
from openai import OpenAI

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ChatMessage
from platforms.base.base_client import BasePlatformClient


class NvidiaClient(BasePlatformClient):
    """NVIDIA NIM API 客户端"""

    platform_name = "nvidia"

    def __init__(self, api_key: str, base_url: str = "https://integrate.api.nvidia.com/v1"):
        os.environ.setdefault('SSL_CERT_FILE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')
        os.environ.setdefault('REQUESTS_CA_BUNDLE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')

        self.api_key = api_key
        self.base_url = base_url
        self._client: OpenAI = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(verify=True, timeout=30)
            )
        return self._client

    def chat(self, model: str, messages: List[ChatMessage], **kwargs) -> str:
        """发送聊天请求"""
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        completion = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            **kwargs
        )

        response = completion.choices[0].message.content
        if response is None and hasattr(completion.choices[0].message, 'reasoning_content'):
            response = completion.choices[0].message.reasoning_content

        return response or ""

    def list_models(self) -> List[dict]:
        """获取可用模型列表"""
        models = self.client.models.list()
        return [{"id": m.id, "name": m.id} for m in models.data]

    def close(self):
        """关闭客户端"""
        if self._client:
            self._client.close()
            self._client = None