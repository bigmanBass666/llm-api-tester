"""
智谱AI免费模型响应速度测试 - 基于通用测试框架

使用方法:
    python scripts/run_zhipu_speed.py
或设置环境变量 ZHIPU_API_KEY 后运行
"""

import os
import sys
import time
import yaml
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import platform_registry  # noqa: F401
from platforms.zhipu.client import ZhipuClient
from src.models import ChatMessage

from crawler.speed_tester import BaseSpeedTestSuite, SpeedTestResult


class ZhipuSpeedTestSuite(BaseSpeedTestSuite):
    """智谱AI速度测试套件"""

    _model_metadata: Dict[str, dict] = {}

    def __init__(self, output_dir: str = "docs", config_path: str = "configs/platforms.yaml"):
        super().__init__(output_dir)
        self._load_config(config_path)

    def _load_config(self, config_path: str):
        """加载平台配置以获取并发数等元数据"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            zhipu_config = config.get('platforms', {}).get('zhipu', {})
            models = zhipu_config.get('models', {}).get('free', [])

            for model in models:
                model_id = model.get('id')
                if model_id:
                    self._model_metadata[model_id] = {
                        'concurrency': model.get('concurrency') or model.get('rate_limit'),
                        'is_free': True,
                        'category': model.get('category', '通用模型'),
                        'description': model.get('note', '')
                    }

        except Exception as e:
            print(f"⚠️  警告: 无法加载配置文件 {config_path}: {e}")
            self._model_metadata = {}

    def _create_client(self):
        """创建智谱客户端"""
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise EnvironmentError("请设置 ZHIPU_API_KEY 环境变量")
        return ZhipuClient(api_key=api_key)

    def _list_models(self) -> List[Dict]:
        """列出所有免费模型"""
        client = self._create_client()
        models = client.list_models()
        return [
            {
                "id": m.id,
                "name": m.name,
                "platform": m.vendor,
                "tags": getattr(m, 'tags', []) or []
            }
            for m in models
        ]

    def get_model_metadata(self, model_id: str) -> dict:
        """获取模型的元数据（并发数、分类等）"""
        return self._model_metadata.get(model_id, {})

    def _test_single_model(self, client, model_info: Dict,
                          test_message: str, max_tokens: int) -> SpeedTestResult:
        """测试单个智谱模型"""
        model_id = model_info["id"]

        result = SpeedTestResult(
            model_id=model_id,
            platform=model_info.get("platform", "zhipu"),
            test_message=test_message,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        messages = [ChatMessage(role="user", content=test_message)]

        try:
            start = time.time()
            ttft_recorded = False
            full_response = ""

            for chunk in client.chat_stream(
                model_id, messages,
                max_tokens=max_tokens,
                temperature=0.0
            ):
                if not ttft_recorded:
                    result.ttft = time.time() - start
                    result.first_chunk = str(chunk) if isinstance(chunk, str) else ""
                    ttft_recorded = True
                full_response += str(chunk) if isinstance(chunk, str) else ""

            result.total_time = time.time() - start
            result.full_response = full_response if full_response else None

        except Exception as e:
            err_msg = str(e)
            status = getattr(e, 'status_code', None)

            if (status == 400 or "1212" in err_msg or
                "SSE" in err_msg or "不支持" in err_msg or
                "not support" in err_msg.lower()):

                try:
                    start = time.time()
                    response = client.chat(
                        model_id, messages,
                        max_tokens=max_tokens,
                        temperature=0.0
                    )
                    result.total_time = time.time() - start
                    result.full_response = str(response) if isinstance(response, str) else ""
                    result.ttft = None
                except Exception as e2:
                    result.error = f"降级失败: {str(e2)} (原始: {err_msg})"
                    result.error_type = type(e2).__name__
                    result.total_time = time.time() - start

            elif status == 429 or "429" in err_msg or "访问量过大" in err_msg:
                time.sleep(2)
                try:
                    start = time.time()
                    for chunk in client.chat_stream(
                        model_id, messages,
                        max_tokens=max_tokens,
                        temperature=0.0
                    ):
                        if not ttft_recorded:
                            result.ttft = time.time() - start
                            result.first_chunk = str(chunk) if isinstance(chunk, str) else ""
                            ttft_recorded = True
                        break
                    result.total_time = time.time() - start
                except Exception as e2:
                    result.error = f"重试失败: {str(e2)}"
                    result.error_type = type(e2).__name__
                    result.total_time = time.time() - start
            else:
                result.error = err_msg
                result.error_type = type(e).__name__
                if 'total_time' not in result or result.total_time is None:
                    result.total_time = 0.0

        return result


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="智谱AI免费模型响应速度测试")
    parser.add_argument("--message", default="回复 OK",
                       help="测试消息内容")
    parser.add_argument("--max-tokens", type=int, default=64,
                       help="最大生成token数")
    parser.add_argument("--output-dir", default="docs",
                       help="输出目录")

    args = parser.parse_args()

    suite = ZhipuSpeedTestSuite(output_dir=args.output_dir)

    print(f"开始测试智谱AI免费模型...")
    results = suite.test_all(
        test_message=args.message,
        max_tokens=args.max_tokens
    )

    md_file, json_file = suite.export_all(test_name="zhipu_speed_test")

    print("\n" + "="*60)
    print("📈 测试完成!")
    summary = suite.generate_summary()
    print(f"   成功: {summary.get('success', 0)} / 失败: {summary.get('failed', 0)}")

    if summary.get('streaming_supported', 0) > 0:
        print(f"   🏆 最快TTFT: {summary.get('ttft_min', 'N/A'):.3f}s")
        print(f"   ⚡ 最快总耗时: {summary.get('total_min', 'N/A'):.3f}s")


if __name__ == "__main__":
    main()
