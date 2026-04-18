"""
NVIDIA 模型批量测试入口脚本

使用方法:
    python scripts/test_nvidia.py
    python scripts/test_nvidia.py -n 50 -c 3
"""

import asyncio
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_loader import ConfigLoader
from platforms.nvidia import NvidiaScraper, NvidiaTester
from report import ReportGenerator


async def main():
    ConfigLoader.load_env('.env.local')
    defaults = ConfigLoader.get_platform_defaults('nvidia')

    parser = argparse.ArgumentParser(description="NVIDIA 模型批量测试")
    parser.add_argument("-n", "--number", type=int,
                       default=defaults.get('number', 20),
                       help="测试的模型数量")
    parser.add_argument("-c", "--concurrency", type=int,
                       default=defaults.get('concurrency', 10),
                       help="并发测试数量")
    parser.add_argument("--timeout", type=int,
                       default=defaults.get('timeout', 60),
                       help="单个模型测试超时时间(秒)")

    args = parser.parse_args()

    print("=" * 60)
    print("🔍 NVIDIA 模型批量测试")
    print("=" * 60)

    api_key = os.getenv('NVIDIA_API_KEY')

    if not api_key:
        print("❌ 错误: 请先配置 NVIDIA_API_KEY")
        print("   参考: docs/API_KEY_SETUP.md")
        sys.exit(1)

    print(f"📋 配置:")
    print(f"   模型数量: {args.number}")
    print(f"   并发数: {args.concurrency}")
    print(f"   超时时间: {args.timeout}s")
    print()

    scraper = NvidiaScraper(headless=True)
    models = await scraper.scrape(limit=args.number)
    await scraper.close()

    if not models:
        print("❌ 错误: 无法获取模型列表")
        sys.exit(1)

    print(f"\n🚀 开始测试 {len(models)} 个模型...")
    print("-" * 60)

    tester = NvidiaTester(api_key=api_key)
    results = await tester.batch_test(models, concurrency=args.concurrency, timeout=args.timeout)

    print()
    print("-" * 60)
    print("📊 测试完成! 生成报告...")

    generator = ReportGenerator(platform="nvidia")
    files = generator.generate(results)

    print(f"✅ Markdown 报告: {files['markdown']}")
    print(f"✅ JSON 报告: {files['json']}")

    summary = {
        'success': sum(1 for r in results if r.status == 'success'),
        'failed': sum(1 for r in results if r.status == 'failed'),
        'timeout': sum(1 for r in results if r.status == 'timeout'),
    }

    print()
    print("📈 结果摘要:")
    print(f"   ✅ 成功: {summary['success']}")
    print(f"   ❌ 失败: {summary['failed']}")
    print(f"   ⏰ 超时: {summary['timeout']}")


if __name__ == "__main__":
    asyncio.run(main())