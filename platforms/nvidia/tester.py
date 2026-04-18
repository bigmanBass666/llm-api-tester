"""
NVIDIA 模型测试器
"""

import time
from typing import List
import httpx
from openai import OpenAI

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ModelInfo, TestResult, ChatMessage
from platforms.base.base_tester import BaseTester


class NvidiaTester(BaseTester):
    """NVIDIA 模型测试器"""

    platform_name = "nvidia"

    def __init__(self, api_key: str):
        os.environ.setdefault('SSL_CERT_FILE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')
        os.environ.setdefault('REQUESTS_CA_BUNDLE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')

        self.api_key = api_key
        self.base_url = "https://integrate.api.nvidia.com/v1"

    async def test_single(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        """测试单个模型"""
        start_time = time.time()

        try:
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(verify=True, timeout=timeout)
            )

            response = client.chat.completions.create(
                model=model.id,
                messages=[{"role": "user", "content": "请回复'OK'"}],
                max_tokens=20
            )

            elapsed = time.time() - start_time
            message = response.choices[0].message
            content = message.content or ""

            client.close()

            return TestResult(
                model_id=model.id,
                rank=model.rank,
                status="success",
                response_time=round(elapsed, 2),
                response_preview=content[:100],
                is_downloadable=model.is_downloadable,
                is_free_endpoint=model.is_free_endpoint,
                tags=model.tags
            )

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)

            if "Timeout" in error_msg or "timed out" in error_msg.lower():
                status = "timeout"
            else:
                status = "failed"

            return TestResult(
                model_id=model.id,
                rank=model.rank,
                status=status,
                response_time=round(elapsed, 2),
                error_message=error_msg[:200],
                is_downloadable=model.is_downloadable,
                is_free_endpoint=model.is_free_endpoint,
                tags=model.tags
            )