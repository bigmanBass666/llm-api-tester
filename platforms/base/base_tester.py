"""
测试器基类
定义统一测试接口，提供 OpenAI 兼容 API 的默认测试实现
"""

import time
from typing import List, Optional, Dict, Callable
import asyncio
import httpx
from openai import OpenAI

from src.models import ModelInfo, TestResult, ModelType

class BaseTester:
    """测试器基类，所有平台测试器需继承此类

    子类只需设置 self.api_key 和 self.base_url 即可获得默认的 test_single 实现。
    如需自定义测试逻辑，可覆盖 test_single 方法。
    """

    platform_name: str = "base"
    api_key: str = ""
    base_url: str = ""

    UNSUPPORTED_MODEL_TYPES = {ModelType.EMBEDDING, ModelType.SPEECH}

    _TYPE_HANDLERS: Dict[ModelType, str] = {
        ModelType.TEXT: "test_text_model",
        ModelType.IMAGE_GENERATION: "test_image_model",
        ModelType.IMAGE_EDITING: "test_image_model",
        ModelType.MULTIMODAL: "test_text_model",
    }

    def _model_to_result_kwargs(self, model: ModelInfo) -> dict:
        return {
            "model_id": model.id,
            "model_type": model.model_type.value,
            "rank": model.rank,
            "is_downloadable": model.is_downloadable,
            "is_free_endpoint": model.is_free_endpoint,
            "tags": model.tags,
            "call_volume": model.call_volume,
            "published_at": model.published_at,
            "deprecation_info": model.deprecation_info,
            "endpoint_type": model.endpoint_type,
            "inference_provider": model.inference_provider,
            "created_at": model.created_at,
            "api_owned_by": model.api_owned_by,
            "is_hosted": model.is_hosted,
        }

    def _classify_error(self, error: Exception) -> str:
        """根据异常类型判定测试状态（timeout / failed）"""
        error_msg = str(error)
        if "Timeout" in error_msg or "timed out" in error_msg.lower():
            return "timeout"
        return "failed"

    async def test_single(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        if model.model_type in self.UNSUPPORTED_MODEL_TYPES:
            return TestResult(
                **self._model_to_result_kwargs(model),
                status="skipped",
                response_time=0.0,
                error_message=f"{model.model_type.value} model - test not supported",
            )

        handler_name = self._TYPE_HANDLERS.get(model.model_type)
        if handler_name:
            handler = getattr(self, handler_name)
            return await handler(model, timeout)

        return TestResult(
            **self._model_to_result_kwargs(model),
            status="failed",
            response_time=0.0,
            error_message=f"Unsupported model type: {model.model_type.value}",
        )

    async def test_text_model(self, model: ModelInfo, timeout: int = 60) -> TestResult:
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
            content = response.choices[0].message.content or ""

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

    async def test_image_model(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        start_time = time.time()

        try:
            from src.platform_registry import registry, ensure_platform_registered
            ensure_platform_registered(self.platform_name)
            client = registry.create_client(self.platform_name, api_key=self.api_key)

            result = client.generate_image(
                model=model.id,
                prompt="a photo of a cat",
                width=1024,
                height=1024,
            )

            elapsed = time.time() - start_time
            client.close()

            if result.get("success"):
                size_kb = result["image_size_bytes"] / 1024
                dims = result.get("image_dimensions", "unknown")
                steps = result.get("generation_steps", "?")
                ttfb = result.get("ttfb")
                decode = result.get("decode_time")
                parts = [f"[image: {dims}", f"{size_kb:.1f}KB", f"steps={steps}"]
                if ttfb is not None:
                    parts.append(f"ttfb={ttfb:.2f}s")
                if decode is not None:
                    parts.append(f"decode={decode:.2f}s")
                preview = ", ".join(parts) + "]"
                return TestResult(
                    **self._model_to_result_kwargs(model),
                    status="success",
                    response_time=round(elapsed, 2),
                    response_preview=preview,
                )
            else:
                return TestResult(
                    **self._model_to_result_kwargs(model),
                    status="failed",
                    response_time=round(elapsed, 2),
                    error_message="Image generation returned failure",
                )

        except Exception as e:
            elapsed = time.time() - start_time
            return TestResult(
                **self._model_to_result_kwargs(model),
                status=self._classify_error(e),
                response_time=round(elapsed, 2),
                error_message=str(e)[:200],
            )

    async def batch_test(self, models: List[ModelInfo],
                        concurrency: int = 3,
                        timeout: int = 60) -> List[TestResult]:
        results = []
        semaphore = asyncio.Semaphore(concurrency)

        async def test_with_semaphore(model, index):
            async with semaphore:
                result = await self.test_single(model, timeout)
                self.log_progress(index + 1, result)
                return result

        tasks = [test_with_semaphore(model, i) for i, model in enumerate(models)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                continue
            valid_results.append(r)

        return valid_results

    def log_progress(self, current: int, result: TestResult):
        model_id = result.model_id
        status = result.status
        response_time = result.response_time

        if status == "success":
            print(f"\r[{current}] ✅ {model_id} - {response_time:.2f}s")
        elif status == "failed":
            print(f"\r[{current}] ❌ {model_id} - {result.error_message[:50]}")
        elif status == "timeout":
            print(f"\r[{current}] ⏰ {model_id} - timeout")
        else:
            print(f"\r[{current}] ❓ {model_id} - {status}")
