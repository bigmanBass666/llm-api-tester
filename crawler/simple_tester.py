"""
简化的 NVIDIA 模型批量测试器
不依赖 Playwright，使用已知热门模型列表
"""

import os
import asyncio
import time
import json
from typing import List
import httpx
from openai import OpenAI

from models import ModelInfo, ModelStore


class SimpleModelTester:
    """简化模型测试器"""

    def __init__(self, api_key: str = None):
        # 设置 SSL 证书
        os.environ.setdefault('SSL_CERT_FILE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')
        os.environ.setdefault('REQUESTS_CA_BUNDLE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')

        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 NVIDIA_API_KEY 环境变量或提供 api_key 参数")

    def get_popular_models(self, limit: int = 50) -> List[ModelInfo]:
        """获取已知热门模型列表（模拟热度排序）"""

        # 已知的热门模型（按热度排序）
        popular_models = [
            # 已测试可用的模型
            "qwen/qwen3-coder-480b-a35b-instruct",
            "google/gemma-4-31b-it",
            "meta/llama-4-maverick-17b-128e-instruct",
            "deepseek-ai/deepseek-v3.1-terminus",
            "minimaxai/minimax-m2.7",
            "moonshotai/kimi-k2-instruct-0905",
            "z-ai/glm4.7",
            "stepfun-ai/step-3.5-flash",
            "qwen/qwen3.5-122b-a10b",
            "google/gemma-7b",
            "microsoft/phi-3-mini-128k-instruct",

            # 其他热门模型
            "qwen/qwen3-next-80b-a3b-instruct",
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "deepseek-ai/deepseek-v3.2",
            "deepseek-ai/deepseek-v3.1",
            "moonshotai/kimi-k2.5",
            "z-ai/glm5",
            "openai/gpt-oss-120b",
            "qwen/qwen3.5-397b-a17b",
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-nano-30b-a3b",
            "nvidia/nv-embedqa-e5-v5",
            "baai/bge-m3",
            "minimaxai/minimax-m2.5",
            "meta/llama-3.1-nemotron-nano-vl-8b-v1",
            "openai/gpt-oss-20b",
            "meta/llama-nemotron-embed-vl-1b-v2",
        ]

        models = []
        for i, model_id in enumerate(popular_models[:limit], 1):
            vendor = model_id.split("/")[0]
            models.append(ModelInfo(
                id=model_id,
                name=model_id,
                vendor=vendor,
                rank=i,
                is_available=True,
                test_status="pending"
            ))

        return models

    def test_single_model(self, model: ModelInfo, timeout: int = 60) -> ModelInfo:
        """测试单个模型"""
        print(f"🧪 测试模型 #{model.rank}: {model.id}")

        model.test_status = "testing"
        start_time = time.time()

        try:
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=self.api_key,
                http_client=httpx.Client(verify=False, timeout=timeout)
            )

            # 简单测试：回复 OK
            response = client.chat.completions.create(
                model=model.id,
                messages=[{"role": "user", "content": "请回复'OK'"}],
                max_tokens=50,
                temperature=0.7
            )

            elapsed = time.time() - start_time
            message = response.choices[0].message

            model.test_status = "success"
            model.response_time = elapsed
            model.token_usage = response.usage.total_tokens if response.usage else 0
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")

            print(f"✅ #{model.rank} {model.id} - {elapsed:.2f}s")

            return model

        except Exception as e:
            elapsed = time.time() - start_time
            model.test_status = "failed" if elapsed < timeout else "timeout"
            model.response_time = elapsed
            model.error_message = str(e)[:200]  # 截断错误信息
            model.test_date = time.strftime("%Y-%m-%d %H:%M:%S")

            status_icon = "❌" if elapsed < timeout else "⏰"
            print(f"{status_icon} #{model.rank} {model.id} - {elapsed:.2f}s - {type(e).__name__}")

            return model

    async def test_model_async(self, model: ModelInfo, timeout: int = 60) -> ModelInfo:
        """异步测试单个模型"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.test_single_model, model, timeout
        )

    async def test_batch_models(self, models: List[ModelInfo],
                              concurrency: int = 5,
                              timeout: int = 60) -> List[ModelInfo]:
        """批量测试模型"""
        print(f"🚀 开始批量测试 {len(models)} 个模型 (并发数: {concurrency})")
        print("=" * 60)

        results = []
        semaphore = asyncio.Semaphore(concurrency)

        async def test_with_semaphore(model):
            async with semaphore:
                return await self.test_model_async(model, timeout)

        tasks = [test_with_semaphore(model) for model in models]

        # 分批执行，避免一次性创建太多连接
        batch_size = concurrency * 2
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"⚠️  任务异常: {result}")
                else:
                    results.append(result)

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
                }
                for m in successful_models
            ],
            "failed_models": [
                {
                    "rank": m.rank,
                    "id": m.id,
                    "status": m.test_status,
                    "error": m.error_message,
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


async def test_popular_models(limit: int = 50, concurrency: int = 5):
    """测试热门模型"""
    print("🎯 NVIDIA 模型批量测试（简化版）")
    print("=" * 60)

    # 获取热门模型列表
    tester = SimpleModelTester()
    models = tester.get_popular_models(limit)

    print(f"✅ 使用 {len(models)} 个热门模型")

    # 批量测试
    print("2. 开始批量测试...")
    results = await tester.test_batch_models(models, concurrency=concurrency)

    # 生成报告
    print("3. 生成测试报告...")
    report = tester.generate_report(results)

    # 保存报告
    report_file = f"crawler/reports/simple_test_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    save_report(report, report_file)

    # 打印摘要
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
    asyncio.run(test_popular_models(20, 3))