"""
NVIDIA 模型批量测试器
"""

import os
import time
import asyncio
import httpx
from typing import List, Optional
from openai import OpenAI

from .models import ModelInfo, ModelStore, is_reasoning_model, get_reasoning_effort
from .logger import ModelTestLogger


class ModelTester:
    """模型测试器"""

    def __init__(self, api_key: Optional[str] = None, logger: Optional[ModelTestLogger] = None):
        from src.ssl_config import setup_ssl_certificates
        setup_ssl_certificates()

        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 NVIDIA_API_KEY 环境变量或提供 api_key 参数")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.logger = logger

    def test_single_model(self, model: ModelInfo, timeout: int = 60,
                         force_reasoning: bool = False,
                         force_normal: bool = False) -> ModelInfo:
        """测试单个模型

        Args:
            model: 模型信息
            timeout: 超时时间（秒）
            force_reasoning: 强制使用推理模式测试
            force_normal: 强制使用普通模式测试
        """
        if self.logger and self.logger.is_tested(model.id):
            self.logger.log('INFO', 'skip', model_id=model.id, reason='already_tested')
            print(f"⏭️  跳过 #{model.rank} {model.id}（已完成）")
            return model

        if self.logger:
            self.logger.log_test_start(model.id, model.rank)

        print(f"🧪 测试模型 #{model.rank}: {model.id}")

        model.test_status = "testing"
        start_time = time.time()

        # 判断是否为推理模型
        use_reasoning_mode = force_reasoning or (not force_normal and is_reasoning_model(model.id))

        if use_reasoning_mode:
            print(f"   🔄 使用推理模式测试")
            return self._test_reasoning_model(model, timeout)
        else:
            return self._test_normal_model(model, timeout)

    def _test_reasoning_model(self, model: ModelInfo, timeout: int = 120) -> ModelInfo:
        """测试推理模型（使用流式输出）"""
        from .models import get_reasoning_effort

        reasoning_effort = get_reasoning_effort(model.id)
        extra_body = {
            "chat_template_kwargs": {
                "thinking": True,
                "reasoning_effort": reasoning_effort
            }
        }

        try:
            start_time = time.time()
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(verify=False, timeout=timeout)
            )

            # 推理模型必须使用流式输出
            response = client.chat.completions.create(
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

            # 处理流式响应
            for chunk in response:
                if not hasattr(chunk, 'choices') or not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # 提取推理内容
                reasoning = getattr(delta, 'reasoning', None) or getattr(delta, 'reasoning_content', None)
                if reasoning:
                    reasoning_content += reasoning

                # 提取实际内容
                content = getattr(delta, 'content', None)
                if content:
                    full_content += content

            elapsed = time.time() - start_time

            model.test_status = "success"
            model.response_time = elapsed
            model.token_usage = 0  # 流式响应可能没有 usage
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")
            model.is_reasoning = True
            model.reasoning_effort = reasoning_effort

            if self.logger:
                self.logger.log_test_success(model.id, elapsed, model.token_usage)
                self.logger.mark_tested(model.id)
            else:
                content_preview = full_content[:50] if full_content else "[无]"
                print(f"✅ #{model.rank} {model.id} - {elapsed:.2f}s (内容: {content_preview})")

            return model

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            model.test_status = "timeout"
            model.response_time = elapsed
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")
            model.is_reasoning = True

            if self.logger:
                self.logger.log_test_timeout(model.id, timeout)
                self.logger.mark_tested(model.id)
            else:
                print(f"⏰ #{model.rank} {model.id} - {elapsed:.2f}s - timeout")

            return model

        except Exception as e:
            elapsed = time.time() - start_time
            model.test_status = "failed"
            model.response_time = elapsed
            model.error_message = str(e)[:500]
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")
            model.is_reasoning = True

            if self.logger:
                self.logger.log_test_error(model.id, type(e).__name__, str(e)[:200])
                self.logger.mark_tested(model.id)
            else:
                print(f"❌ #{model.rank} {model.id} - {elapsed:.2f}s - {type(e).__name__}: {str(e)[:100]}")

            return model

    def _test_normal_model(self, model: ModelInfo, timeout: int = 60) -> ModelInfo:
        """测试普通模型（非推理模型）"""
        start_time = time.time()

        try:
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(verify=False, timeout=timeout)
            )

            # 普通模型使用标准调用
            response = client.chat.completions.create(
                model=model.id,
                messages=[{"role": "user", "content": "请回复'OK'"}],
                max_tokens=50,
                temperature=0.7
            )

            elapsed = time.time() - start_time

            model.test_status = "success"
            model.response_time = elapsed
            model.token_usage = response.usage.total_tokens if response.usage else 0
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")

            if self.logger:
                self.logger.log_test_success(model.id, elapsed, model.token_usage)
                self.logger.mark_tested(model.id)
            else:
                print(f"✅ #{model.rank} {model.id} - {elapsed:.2f}s")

            return model

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            model.test_status = "timeout"
            model.response_time = elapsed
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")

            if self.logger:
                self.logger.log_test_timeout(model.id, timeout)
                self.logger.mark_tested(model.id)
            else:
                print(f"⏰ #{model.rank} {model.id} - {elapsed:.2f}s - timeout")

            return model

        except Exception as e:
            elapsed = time.time() - start_time
            model.test_status = "failed"
            model.response_time = elapsed
            model.error_message = str(e)[:500]
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")

            if self.logger:
                self.logger.log_test_error(model.id, type(e).__name__, str(e)[:200])
                self.logger.mark_tested(model.id)
            else:
                print(f"❌ #{model.rank} {model.id} - {elapsed:.2f}s - {type(e).__name__}: {str(e)[:100]}")

            return model

    async def test_model_async(self, model: ModelInfo, timeout: int = 60,
                              force_reasoning: bool = False,
                              force_normal: bool = False) -> ModelInfo:
        """异步测试单个模型"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.test_single_model, model, timeout, force_reasoning, force_normal
        )

    async def test_batch_models(self, models: List[ModelInfo],
                              concurrency: int = 5,
                              timeout: int = 60,
                              timeout_reasoning: int = 180,
                              force_reasoning: bool = False,
                              force_normal: bool = False) -> List[ModelInfo]:
        """批量测试模型

        Args:
            models: 模型列表
            concurrency: 并发数
            timeout: 普通模型超时时间（秒）
            timeout_reasoning: 推理模型超时时间（秒，默认180秒）
            force_reasoning: 强制所有模型使用推理模式
            force_normal: 强制所有模型使用普通模式
        """
        from .models import is_reasoning_model

        if self.logger:
            self.logger.log('INFO', 'batch_start', total=len(models), concurrency=concurrency)
        else:
            print(f"🚀 开始批量测试 {len(models)} 个模型 (并发数: {concurrency})")
            print("=" * 60)

        results = []
        semaphore = asyncio.Semaphore(concurrency)

        async def test_with_semaphore(model):
            async with semaphore:
                # 根据是否为推理模型选择超时时间
                if is_reasoning_model(model.id) and not force_normal:
                    model_timeout = timeout_reasoning
                else:
                    model_timeout = timeout

                result = await self.test_model_async(model, model_timeout, force_reasoning, force_normal)
                # 记录进度
                if self.logger:
                    completed = len(results) + 1
                    self.logger.log('INFO', 'progress',
                                   model_id=model.id,
                                   completed=completed,
                                   total=len(models))
                return result

        tasks = [test_with_semaphore(model) for model in models]

        # 分批执行，避免一次性创建太多连接
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
            # 统计结果
            total = len(results)
            successful = sum(1 for m in results if m.test_status == "success")
            failed = sum(1 for m in results if m.test_status == "failed")
            timeout_count = sum(1 for m in results if m.test_status == "timeout")
            self.logger.log_batch_complete(total, successful, failed, timeout_count)
        else:
            print(f"✅ 批次完成: {len(results)} 个模型已测试")

        return results

    def generate_report(self, models: List[ModelInfo]) -> dict:
        """生成测试报告"""
        summary = {
            "total": len(models),
            "success": sum(1 for m in models if m.test_status == "success"),
            "failed": sum(1 for m in models if m.test_status == "failed"),
            "timeout": sum(1 for m in models if m.test_status == "timeout"),
            "testing": sum(1 for m in models if m.test_status == "testing"),
            "pending": sum(1 for m in models if m.test_status == "pending"),
        }

        # 成功模型按响应时间排序
        successful_models = sorted(
            [m for m in models if m.test_status == "success"],
            key=lambda x: x.response_time
        )

        # 失败模型
        failed_models = [m for m in models if m.test_status in ("failed", "timeout")]

        return {
            "summary": summary,
            "successful_models": [
                {
                    "rank": m.rank,
                    "id": m.id,
                    "response_time": m.response_time,
                    "token_usage": m.token_usage,
                    "tags": getattr(m, 'tags', []) or []
                }
                for m in successful_models
            ],
            "failed_models": [
                {
                    "rank": m.rank,
                    "id": m.id,
                    "status": m.test_status,
                    "error": m.error_message,
                    "tags": getattr(m, 'tags', []) or []
                }
                for m in failed_models
            ],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


def save_report(report: dict, filename: str):
    """保存测试报告"""
    import json

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📊 测试报告已保存: {filename}")


async def test_top_models(limit: int = 50, concurrency: int = 5,
                          use_logger: bool = True, resume: bool = False,
                          sort_by: str = "popular",
                          filter_text_models: bool = True,
                          reasoning_timeout: int = 180,
                          force_reasoning: bool = False,
                          force_normal: bool = False,
                          manual_reasoning_models: list = None):
    """测试前N个热门模型

    Args:
        limit: 测试的模型数量
        concurrency: 并发数
        use_logger: 是否使用日志系统
        resume: 是否启用断点续传（默认关闭）
        sort_by: 排序方式，'popular' 或 'recent'
        filter_text_models: 是否过滤非文本模型（默认 True）
        reasoning_timeout: 推理模型超时时间（秒）
        force_reasoning: 强制所有模型使用推理模式
        force_normal: 强制所有模型使用普通模式
        manual_reasoning_models: 手动指定的推理模型ID列表
    """
    from .scraper import scrape_top_models
    from .logger import create_logger

    logger = create_logger(resume=resume) if use_logger else None
    if logger:
        logger.log_phase('start', total_models=limit, concurrency=concurrency)
    else:
        print("🎯 NVIDIA 模型批量测试")
        print("=" * 60)

    # 爬取模型列表
    if logger:
        logger.log_phase('scraping')
    else:
        print("1. 爬取模型列表...")

    models = await scrape_top_models(limit, sort_by=sort_by,
                                    filter_text_models=filter_text_models)

    if not models:
        if logger:
            logger.log('ERROR', 'no_models_fetched')
        else:
            print("❌ 无法获取模型列表")
        return

    # 处理手动指定的推理模型
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

    # 批量测试
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

    # 保存断点（如果使用）
    if logger and resume:
        logger.save_checkpoint()

    # 生成报告
    if logger:
        logger.log_phase('reporting')
    else:
        print("3. 生成测试报告...")

    report = tester.generate_report(results)

    # 保存报告
    report_file = f"crawler/reports/test_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    save_report(report, report_file)

    # 记录报告生成
    if logger:
        logger.log_report_generated(report_file)

    # 打印摘要（即使有logger也给用户简短摘要）
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
    # 测试
    asyncio.run(test_top_models(10, 3))