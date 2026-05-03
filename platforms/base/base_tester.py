"""
测试器基类
定义统一测试接口，提供 OpenAI 兼容 API 的默认测试实现
"""

import time
from typing import List, Optional
import asyncio
import httpx
from openai import OpenAI
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ModelInfo, TestResult, ModelType


class BaseTester:
    """测试器基类，所有平台测试器需继承此类

    子类只需设置 self.api_key 和 self.base_url 即可获得默认的 test_single 实现。
    如需自定义测试逻辑，可覆盖 test_single 方法。
    """

    platform_name: str = "base"
    api_key: str = ""
    base_url: str = ""

    async def test_single(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        if model.model_type == ModelType.TEXT:
            return await self.test_text_model(model, timeout)
        elif model.model_type == ModelType.IMAGE_GENERATION:
            return await self.test_image_model(model, timeout)
        else:
            return TestResult(
                model_id=model.id,
                model_type=model.model_type.value,
                rank=model.rank,
                status="failed",
                response_time=0.0,
                error_message=f"Unsupported model type: {model.model_type.value}",
                is_downloadable=model.is_downloadable,
                is_free_endpoint=model.is_free_endpoint,
                tags=model.tags,
                call_volume=model.call_volume,
                published_at=model.published_at,
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
                model_id=model.id,
                model_type=model.model_type.value,
                rank=model.rank,
                status="success",
                response_time=round(elapsed, 2),
                response_preview=content[:100],
                is_downloadable=model.is_downloadable,
                is_free_endpoint=model.is_free_endpoint,
                tags=model.tags,
                call_volume=model.call_volume,
                published_at=model.published_at,
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
                model_type=model.model_type.value,
                rank=model.rank,
                status=status,
                response_time=round(elapsed, 2),
                error_message=error_msg[:200],
                is_downloadable=model.is_downloadable,
                is_free_endpoint=model.is_free_endpoint,
                tags=model.tags,
                call_volume=model.call_volume,
                published_at=model.published_at,
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
                    model_id=model.id,
                    model_type=model.model_type.value,
                    rank=model.rank,
                    status="success",
                    response_time=round(elapsed, 2),
                    response_preview=preview,
                    is_downloadable=model.is_downloadable,
                    is_free_endpoint=model.is_free_endpoint,
                    tags=model.tags,
                    call_volume=model.call_volume,
                    published_at=model.published_at,
                )
            else:
                return TestResult(
                    model_id=model.id,
                    model_type=model.model_type.value,
                    rank=model.rank,
                    status="failed",
                    response_time=round(elapsed, 2),
                    error_message="Image generation returned failure",
                    is_downloadable=model.is_downloadable,
                    is_free_endpoint=model.is_free_endpoint,
                    tags=model.tags,
                    call_volume=model.call_volume,
                    published_at=model.published_at,
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
                model_type=model.model_type.value,
                rank=model.rank,
                status=status,
                response_time=round(elapsed, 2),
                error_message=error_msg[:200],
                is_downloadable=model.is_downloadable,
                is_free_endpoint=model.is_free_endpoint,
                tags=model.tags,
                call_volume=model.call_volume,
                published_at=model.published_at,
            )

    async def batch_test(self, models: List[ModelInfo],
                        concurrency: int = 3,
                        timeout: int = 60) -> List[TestResult]:
        """
        批量测试模型
        Args:
            models: 模型列表
            concurrency: 并发数
            timeout: 单个模型超时时间
        Returns:
            测试结果列表
        """
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
        """输出进度日志"""
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
