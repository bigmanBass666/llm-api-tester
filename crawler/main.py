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

# 加载环境变量（从 .env.local 等文件）
from src.config_loader import ConfigLoader
ConfigLoader.load_env()

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
    parser.add_argument("-c", "--concurrency", type=int, default=5,
                       help="并发测试数量 (默认: 5)")
    parser.add_argument("--scrape-only", action="store_true",
                       help="仅爬取模型列表，不测试")
    parser.add_argument("--timeout", type=int, default=60,
                       help="单个模型测试超时时间(秒) (默认: 60)")
    parser.add_argument("--sort-by", type=str, default="popular",
                       choices=["popular", "recent"],
                       help="排序方式: popular(热度) 或 recent(最新) (默认: popular)")
    parser.add_argument("--no-log", action="store_true",
                       help="禁用日志系统")
    parser.add_argument("--log-dir", type=str, default="logs",
                       help="日志目录 (默认: logs)")
    parser.add_argument("--resume", action="store_true",
                       help="启用断点续传（跳过已测试的模型）")
    parser.add_argument("--filter-text", action="store_true",
                       default=True,
                       help="只爬取和测试文字模型（过滤语音、图像、嵌入等非文字模型）【默认启用】")
    parser.add_argument("--no-filter", action="store_true",
                       help="禁用非文字模型过滤（将测试所有模型，包括嵌入/图像/OCR等）")
    parser.add_argument("--reasoning-model", type=str, action="append",
                       help="手动指定推理模型ID（可多次使用），将使用推理模式测试")
    parser.add_argument("--force-normal", action="store_true",
                       help="强制所有模型使用普通模式测试（禁用自动推理模型检测）")
    parser.add_argument("--reasoning-timeout", type=int, default=180,
                       help="推理模型超时时间(秒) (默认: 180)")

    args = parser.parse_args()

    print_banner()

    print(f"📋 配置信息:")
    print(f"   模型数量: {args.number}")
    print(f"   并发数: {args.concurrency}")
    print(f"   超时时间: {args.timeout}s")
    print(f"   排序方式: {args.sort_by}")
    print(f"   仅爬取: {args.scrape_only}")
    print(f"   过滤非文字模型: {'✅ 启用（默认）' if not args.no_filter else '❌ 禁用（--no-filter）'}")
    print()

    try:
        # 初始化日志器（除非禁用）
        logger = None
        if not args.no_log:
            from crawler.logger import create_logger
            logger = create_logger(log_dir=args.log_dir, resume=args.resume)

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

            models = await scrape_top_models(args.number, sort_by=args.sort_by, filter_text_models=not args.no_filter)

            if models:
                if logger:
                    logger.log('INFO', 'scrape_complete', total=len(models))
                else:
                    print(f"✅ 成功爬取 {len(models)} 个模型:")
                    for m in models:
                        print(f"   #{m.rank:2d} {m.id}")
                    print(f"\n📊 过滤统计:")
                    print(f"   过滤模式: {'文字模型过滤（默认）' if not args.no_filter else '全量模式（包含非文字模型）'}")
                    print(f"   获取数量: {len(models)} / 请求 {args.number} 个")
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
                resume=args.resume,
                sort_by=args.sort_by,
                filter_text_models=not args.no_filter,
                reasoning_timeout=args.reasoning_timeout,
                force_reasoning=bool(args.reasoning_model),
                force_normal=args.force_normal,
                manual_reasoning_models=args.reasoning_model
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
