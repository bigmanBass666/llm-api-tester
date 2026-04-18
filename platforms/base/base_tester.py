"""
测试器基类
定义统一测试接口
"""

from abc import ABC, abstractmethod
from typing import List
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models import ModelInfo, TestResult


class BaseTester(ABC):
    """测试器基类，所有平台测试器需继承此类"""

    platform_name: str = "base"

    @abstractmethod
    async def test_single(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        """
        测试单个模型
        Args:
            model: 模型信息
            timeout: 超时时间(秒)
        Returns:
            测试结果
        """
        pass

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