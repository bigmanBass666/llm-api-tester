"""
NVIDIA 模型批量测试 - 主入口
支持按官方热度排序测试前N个模型
"""

import asyncio
import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.tester import test_top_models
from crawler.scraper import scrape_top_models
from crawler.models import ModelStore


def print_banner():
    """打印横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                            NVIDIA 模型批量测试器                             ║
║                                                                              ║
║   🎯 按官方热度排序测试前N个模型                                             ║
║   📊 自动爬取模型列表并批量测试                                              ║
║   📈 生成详细测试报告                                                        ║
║   ⚡ 支持并发测试，提高效率                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="NVIDIA 模型批量测试")
    parser.add_argument("-n", "--number", type=int, default=20,
                       help="测试的模型数量 (默认: 20)")
    parser.add_argument("-c", "--concurrency", type=int, default=3,
                       help="并发测试数量 (默认: 3)")
    parser.add_argument("--scrape-only", action="store_true",
                       help="仅爬取模型列表，不测试")
    parser.add_argument("--timeout", type=int, default=60,
                       help="单个模型测试超时时间(秒) (默认: 60)")
    parser.add_argument("--no-log", action="store_true",
                       help="禁用日志系统")
    parser.add_argument("--log-dir", type=str, default="logs",
                       help="日志目录 (默认: logs)")
    parser.add_argument("--no-resume", action="store_true",
                       help="禁用断点续传（重新测试所有模型）")

    args = parser.parse_args()

    print_banner()

    print(f"📋 配置信息:")
    print(f"   模型数量: {args.number}")
    print(f"   并发数: {args.concurrency}")
    print(f"   超时时间: {args.timeout}s")
    print(f"   仅爬取: {args.scrape_only}")
    print()

    try:
        # 初始化日志器（除非禁用）
        logger = None
        if not args.no_log:
            from crawler.logger import create_logger
            logger = create_logger(log_dir=args.log_dir)

            if logger:
                logger.log_phase('init',
                               models=args.number,
                               concurrency=args.concurrency,
                               scrape_only=args.scrape_only,
                               timeout=args.timeout)

        if args.scrape_only:
            # 仅爬取模式
            if logger:
                logger.log_phase('scrape_only')
            else:
                print("🔍 仅爬取模型列表...")

            models = await scrape_top_models(args.number)

            if models:
                if logger:
                    logger.log('INFO', 'scrape_complete', total=len(models))
                else:
                    print(f"✅ 成功爬取 {len(models)} 个模型:")
                    for m in models:
                        print(f"   #{m.rank:2d} {m.id}")
            else:
                if logger:
                    logger.log('ERROR', 'scrape_failed')
                else:
                    print("❌ 爬取失败")

        else:
            # 完整测试模式
            await test_top_models(
                limit=args.number,
                concurrency=args.concurrency,
                use_logger=not args.no_log,
                resume=not args.no_resume
            )

        if logger:
            logger.log_phase('complete')
        else:
            print("\n🎉 任务完成!")

    except KeyboardInterrupt:
        if logger:
            logger.log('WARNING', 'interrupted')
        else:
            print("\n⚠️  用户中断")
    except Exception as e:
        if logger:
            logger.log('ERROR', 'fatal_error', error_msg=str(e))
        else:
            print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        sys.exit(1)