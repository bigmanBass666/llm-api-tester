"""
NVIDIA 模型批量测试器
"""

import os
import time
import asyncio
import httpx
from typing import List, Optional

from .models import ModelInfo, is_reasoning_model, get_reasoning_effort
from src.models import TestResult
from .logger import ModelTestLogger
from .errors import APIError, AuthenticationError, RateLimitError, ModelNotFoundError, TimeoutError as APITimeoutError, ServerError


class ModelTester:
    """模型测试器"""

    def __init__(self, api_key: Optional[str] = None, logger: Optional[ModelTestLogger] = None, client=None):
        from src.ssl_config import setup_ssl_certificates
        setup_ssl_certificates()

        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 NVIDIA_API_KEY 环境变量或提供 api_key 参数")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.logger = logger
        self._client = client

        if client is None:
            self._http_client = httpx.AsyncClient(
                verify=False,
                timeout=httpx.Timeout(connect=30, read=180, write=60, pool=10)
            )
        else:
            self._http_client = None

    async def _get_openai_client(self):
        from openai import AsyncOpenAI
        return AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client=self._http_client,
        )

    def _handle_test_error(self, model: ModelInfo, error: Exception, start_time: float, is_reasoning: bool = False) -> TestResult:
        elapsed = time.time() - start_time

        if isinstance(error, (asyncio.TimeoutError, APITimeoutError)):
            status = "timeout"
            error_message = str(error)[:500] if isinstance(error, APITimeoutError) else "请求超时: 服务器响应时间过长"
        elif isinstance(error, AuthenticationError):
            status = "failed"
            error_message = "认证失败: 请检查API Key是否正确"
        elif isinstance(error, RateLimitError):
            status = "failed"
            error_message = "请求频率超限: 请稍后重试"
        elif isinstance(error, ModelNotFoundError):
            status = "failed"
            error_message = f"模型不存在: {error.message}"
        elif isinstance(error, ServerError):
            status = "failed"
            error_message = f"服务器错误({error.status_code}): {error.message}"
        elif isinstance(error, APIError):
            status = "failed"
            error_message = f"API错误: {error.message}"
        else:
            status = "failed"
            error_message = str(error)[:500]

        result = TestResult.from_model_info(
            model,
            status=status,
            response_time=round(elapsed, 2),
            error_message=error_message,
        )

        if self.logger:
            log_method = self.logger.log_test_timeout if status == "timeout" else self.logger.log_test_error
            if status == "timeout":
                log_method(model.id, int(elapsed))
            else:
                log_method(model.id, type(error).__name__, error_message[:200])
            self.logger.mark_tested(model.id)
        else:
            icon = "⏰" if status == "timeout" else "❌"
            detail = "timeout" if status == "timeout" else f"{type(error).__name__}: {str(error)[:100]}"
            print(f"{icon} #{model.rank} {model.id} - {elapsed:.2f}s - {detail}")

        return result

    async def test_single_model(self, model: ModelInfo, timeout: int = 60,
                         force_reasoning: bool = False,
                         force_normal: bool = False) -> TestResult:
        if self.logger and self.logger.is_tested(model.id):
            self.logger.log('INFO', 'skip', model_id=model.id, reason='already_tested')
            print(f"⏭️  跳过 #{model.rank} {model.id}（已完成）")
            return TestResult.from_model_info(model, status="skipped")

        if self.logger:
            self.logger.log_test_start(model.id, model.rank)

        print(f"🧪 测试模型 #{model.rank}: {model.id}")

        use_reasoning_mode = force_reasoning or (not force_normal and is_reasoning_model(model.id))

        if use_reasoning_mode:
            print(f"   🔄 使用推理模式测试")
            return await self._test_reasoning_model(model, timeout)
        else:
            return await self._test_normal_model(model, timeout)

    async def _test_reasoning_model(self, model: ModelInfo, timeout: int = 120) -> TestResult:
        reasoning_effort = get_reasoning_effort(model.id)
        extra_body = {
            "chat_template_kwargs": {
                "thinking": True,
                "reasoning_effort": reasoning_effort
            }
        }

        start_time = time.time()

        try:
            client = await self._get_openai_client()

            response = await client.chat.completions.create(
                model=model.id,
                messages=[{"role": "user", "content": "请回复'OK'"}],
                max_tokens=100,
                temperature=0.7,
                extra_body=extra_body,
                stream=True
            )

            start_time = time.time()
            full_content = ""
            reasoning_content = ""

            async for chunk in response:
                if not hasattr(chunk, 'choices') or not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                reasoning = getattr(delta, 'reasoning', None) or getattr(delta, 'reasoning_content', None)
                if reasoning:
                    reasoning_content += reasoning

                content = getattr(delta, 'content', None)
                if content:
                    full_content += content

            elapsed = time.time() - start_time

            result = TestResult.from_model_info(
                model,
                status="success",
                response_time=round(elapsed, 2),
                response_preview=full_content[:100],
                reasoning_content=reasoning_content,
                token_usage=0,
            )

            if self.logger:
                self.logger.log_test_success(model.id, elapsed, 0)
                self.logger.mark_tested(model.id)
            else:
                content_preview = full_content[:50] if full_content else "[无]"
                print(f"✅ #{model.rank} {model.id} - {elapsed:.2f}s (内容: {content_preview})")

            return result

        except Exception as e:
            return self._handle_test_error(model, e, start_time, is_reasoning=True)

    async def _test_normal_model(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        start_time = time.time()

        try:
            client = await self._get_openai_client()

            response = await client.chat.completions.create(
                model=model.id,
                messages=[{"role": "user", "content": "请回复'OK'"}],
                max_tokens=50,
                temperature=0.7
            )

            elapsed = time.time() - start_time
            token_usage = response.usage.total_tokens if response.usage else 0

            result = TestResult.from_model_info(
                model,
                status="success",
                response_time=round(elapsed, 2),
                response_preview=response.choices[0].message.content[:100] if response.choices[0].message.content else "",
                token_usage=token_usage,
            )

            if self.logger:
                self.logger.log_test_success(model.id, elapsed, token_usage)
                self.logger.mark_tested(model.id)
            else:
                print(f"✅ #{model.rank} {model.id} - {elapsed:.2f}s")

            return result

        except Exception as e:
            return self._handle_test_error(model, e, start_time)

    async def test_model_async(self, model: ModelInfo, timeout: int = 60,
                              force_reasoning: bool = False,
                              force_normal: bool = False) -> TestResult:
        return await self.test_single_model(model, timeout, force_reasoning, force_normal)

    async def test_batch_models(self, models: List[ModelInfo],
                              concurrency: int = 5,
                              timeout: int = 60,
                              timeout_reasoning: int = 180,
                              force_reasoning: bool = False,
                              force_normal: bool = False) -> List[TestResult]:
        from .models import is_reasoning_model

        if self.logger:
            self.logger.log('INFO', 'batch_start', total=len(models), concurrency=concurrency)
        else:
            print(f"🚀 开始批量测试 {len(models)} 个模型 (并发数: {concurrency})")
            print("=" * 60)

        results: List[TestResult] = []
        semaphore = asyncio.Semaphore(concurrency)

        async def test_with_semaphore(model):
            async with semaphore:
                if is_reasoning_model(model.id) and not force_normal:
                    model_timeout = timeout_reasoning
                else:
                    model_timeout = timeout

                result = await self.test_model_async(model, model_timeout, force_reasoning, force_normal)
                if self.logger:
                    completed = len(results) + 1
                    self.logger.log('INFO', 'progress',
                                   model_id=model.id,
                                   completed=completed,
                                   total=len(models))
                return result

        tasks = [test_with_semaphore(model) for model in models]

        batch_size = concurrency * 2
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    if self.logger:
                        self.logger.log('ERROR', 'task_exception', error_msg=str(result))
                    else:
                        print(f"⚠️  任务异常: {result}")
                else:
                    results.append(result)

        if self.logger:
            total = len(results)
            successful = sum(1 for r in results if r.status == "success")
            failed = sum(1 for r in results if r.status == "failed")
            timeout_count = sum(1 for r in results if r.status == "timeout")
            self.logger.log_batch_complete(total, successful, failed, timeout_count)
        else:
            print(f"✅ 批次完成: {len(results)} 个模型已测试")

        return results

    def generate_report(self, results: List[TestResult]) -> dict:
        summary = {
            "total": len(results),
            "success": sum(1 for r in results if r.status == "success"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "timeout": sum(1 for r in results if r.status == "timeout"),
            "testing": sum(1 for r in results if r.status == "testing"),
            "pending": sum(1 for r in results if r.status == "pending"),
        }

        successful_results = sorted(
            [r for r in results if r.status == "success"],
            key=lambda x: x.response_time
        )

        failed_results = [r for r in results if r.status in ("failed", "timeout")]

        return {
            "summary": summary,
            "successful_models": [
                {
                    "rank": r.rank,
                    "id": r.model_id,
                    "response_time": r.response_time,
                    "token_usage": r.token_usage,
                    "tags": r.tags or []
                }
                for r in successful_results
            ],
            "failed_models": [
                {
                    "rank": r.rank,
                    "id": r.model_id,
                    "status": r.status,
                    "error": r.error_message,
                    "tags": r.tags or []
                }
                for r in failed_results
            ],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


def save_report(report: dict, filename: str):
    import json

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📊 测试报告已保存: {filename}")


async def test_top_models(limit: int = 50, concurrency: int = 5,
                          use_logger: bool = True, resume: bool = False,
                          sort_by: str = "popular",
                          filter_text_models: bool = True,
                          model_type_filter=None,
                          reasoning_timeout: int = 180,
                          force_reasoning: bool = False,
                          force_normal: bool = False,
                          manual_reasoning_models: list = None):
    from .scraper import scrape_top_models
    from .logger import create_logger

    logger = create_logger(resume=resume) if use_logger else None
    if logger:
        logger.log_phase('start', total_models=limit, concurrency=concurrency)
    else:
        print("🎯 NVIDIA 模型批量测试")
        print("=" * 60)

    if logger:
        logger.log_phase('scraping')
    else:
        print("1. 爬取模型列表...")

    from src.models import ModelType
    if model_type_filter is None and filter_text_models:
        model_type_filter = ModelType.TEXT
    models = await scrape_top_models(limit, sort_by=sort_by,
                                    model_type_filter=model_type_filter)

    if not models:
        if logger:
            logger.log('ERROR', 'no_models_fetched')
        else:
            print("❌ 无法获取模型列表")
        return

    if manual_reasoning_models:
        for model in models:
            if model.id in manual_reasoning_models:
                model.is_reasoning = True
                from .models import get_reasoning_effort
                model.reasoning_effort = get_reasoning_effort(model.id)
        print(f"🔧 手动指定 {len(manual_reasoning_models)} 个推理模型")

    if logger:
        logger.log('INFO', 'models_fetched', total=len(models))
    else:
        print(f"✅ 获取到 {len(models)} 个模型")

    if logger:
        logger.log_phase('testing')
    else:
        print("2. 开始批量测试...")

    tester = ModelTester(logger=logger) if logger else ModelTester()
    results = await tester.test_batch_models(
        models,
        concurrency=concurrency,
        timeout_reasoning=reasoning_timeout,
        force_reasoning=force_reasoning,
        force_normal=force_normal
    )

    if logger and resume:
        logger.save_checkpoint()

    if logger:
        logger.log_phase('reporting')
    else:
        print("3. 生成测试报告...")

    report = tester.generate_report(results)

    report_file = f"crawler/reports/test_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    save_report(report, report_file)

    if logger:
        logger.log_report_generated(report_file)

    if not logger:
        print("\n" + "=" * 60)
        print("📈 测试摘要:")
        print(f"   总计: {report['summary']['total']}")
        print(f"   成功: {report['summary']['success']} ✅")
        print(f"   失败: {report['summary']['failed']} ❌")
        print(f"   超时: {report['summary']['timeout']} ⏰")

        if report['successful_models']:
            print(f"\n🏆 最快模型:")
            fastest = report['successful_models'][0]
            print(f"   #{fastest['rank']} {fastest['id']} - {fastest['response_time']:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_top_models(10, 3))
