"""
Kimi 模型测试器
使用 Anthropic Messages API 协议（非 OpenAI 兼容）
"""

import time
from typing import List
from platforms.base.base_tester import BaseTester
from platforms.common.openai_compatible_client import KimiClient
from src.models import ModelInfo, TestResult, ChatMessage


class KimiTester(BaseTester):
    """Kimi 模型测试器"""

    platform_name = "kimi"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.kimi.com/coding/"

    async def test_text_model(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        """测试文本模型，使用 KimiClient（Anthropic 协议）"""
        start_time = time.time()

        try:
            client = KimiClient(api_key=self.api_key)
            messages = [ChatMessage(role="user", content="请回复'OK'")]

            content = client.chat(
                model=model.id,
                messages=messages,
                max_tokens=20,
            )

            elapsed = time.time() - start_time
            client.close()

            return TestResult(
                **self._model_to_result_kwargs(model),
                status="success",
                response_time=round(elapsed, 2),
                response_preview=content[:100],
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return TestResult(
                **self._model_to_result_kwargs(model),
                status=self._classify_error(e),
                response_time=round(elapsed, 2),
                error_message=str(e)[:200],
            )
