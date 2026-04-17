"""
批量测试脚本
支持多平台模型测试
"""

import sys
import os
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import registry, NvidiaClient


def test_platform(platform: str, verbose: bool = True):
    """测试指定平台的所有模型"""
    try:
        client = registry.create_client(platform)
    except Exception as e:
        print(f"❌ 无法创建 {platform} 客户端: {e}")
        return {}

    config = registry.get(platform)
    print(f"\n测试平台: {config.display_name}")
    print(f"API URL: {config.default_base_url}")
    print("-" * 60)

    # 测试连接
    print("测试连接...", end=" ")
    if client.test_connection():
        print("✅ 连接成功")
    else:
        print("❌ 连接失败")
        return {}

    # 获取模型列表
    models = client.list_models()
    print(f"\n发现 {len(models)} 个模型")

    # 测试每个模型
    results = {}
    for model in models[:10]:  # 限制测试前10个
        if verbose:
            print(f"\n测试: {model.id}")

        try:
            # 跳过非免费模型
            if platform == "nvidia":
                free_models = NvidiaClient.FREE_MODELS.values()
                if model.id not in free_models:
                    if verbose:
                        print(f"  ⏭️ 跳过（非预定义免费模型）")
                    continue

            from src.base_client import ChatMessage
            response = client.chat(
                model.id,
                [ChatMessage(role="user", content="Hi")],
                max_tokens=20
            )

            if response and response.strip():
                results[model.id] = ("✅ 成功", response[:50])
                if verbose:
                    print(f"  ✅ 成功: {response[:50]}...")
            else:
                results[model.id] = ("⚠️ 空回复", "")
                if verbose:
                    print(f"  ⚠️ 空回复")

        except Exception as e:
            results[model.id] = (f"❌ {type(e).__name__}", str(e)[:50])
            if verbose:
                print(f"  ❌ 失败: {type(e).__name__}")

    client.close()

    # 打印汇总
    if verbose:
        print(f"\n{'='*60}")
        print("测试结果汇总:")
        print(f"{'='*60}")

        success = sum(1 for v in results.values() if "成功" in v[0])
        for model_id, (status, _) in results.items():
            print(f"{status} - {model_id}")

        print(f"\n成功: {success}/{len(results)}")

    return results


def test_nvidia_models(verbose: bool = True):
    """专门测试 NVIDIA 免费模型（使用快捷名称）"""
    client = NvidiaClient()
    free_models = NvidiaClient.FREE_MODELS

    print(f"\n测试 NVIDIA 免费模型 ({len(free_models)} 个)")
    print("-" * 60)

    results = {}

    for name, model_id in free_models.items():
        if verbose:
            print(f"测试: {name} ({model_id})")

        try:
            response = client.quick_chat(name, "请回复'OK'")
            if response and response.strip():
                results[name] = ("✅ 成功", response[:50])
                if verbose:
                    print(f"  ✅ 成功: {response[:50]}...")
            else:
                results[name] = ("⚠️ 空回复", "")
                if verbose:
                    print(f"  ⚠️ 空回复")

        except Exception as e:
            results[name] = (f"❌ {type(e).__name__}", str(e)[:30])
            if verbose:
                print(f"  ❌ 失败: {type(e).__name__}")

    client.close()

    if verbose:
        print(f"\n{'='*60}")
        success = sum(1 for v in results.values() if "成功" in v[0])
        for name, (status, _) in results.items():
            print(f"{status} - {name}")
        print(f"\n成功: {success}/{len(results)}")

    return results


def list_available_platforms():
    """列出所有可用平台"""
    platforms = registry.list_available_platforms()
    print("\n可用平台:")
    print("-" * 60)
    for p in platforms:
        print(f"  {p.name:15} - {p.display_name}")
        print(f"                   {p.description[:50]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="批量测试多平台 AI API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/batch_test.py                    # 测试 NVIDIA 免费模型
  python scripts/batch_test.py --platform nvidia  # 测试 NVIDIA 所有模型
  python scripts/batch_test.py --list             # 列出所有可用平台
  python scripts/batch_test.py -m minimax-m2.7   # 测试单个模型
        """
    )

    parser.add_argument(
        "--platform", "-p",
        choices=["nvidia", "aliyun", "tencent", "zhipu", "ollama"],
        help="指定平台 (默认: nvidia)"
    )
    parser.add_argument("--model", "-m", help="只测试单个模型 (NVIDIA 快捷名称)")
    parser.add_argument("--message", default="请回复'OK'", help="测试消息")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用平台")
    parser.add_argument("--quiet", "-q", action="store_true", help="安静模式")

    args = parser.parse_args()

    if args.list:
        list_available_platforms()
    elif args.model:
        # 单模型测试 (NVIDIA)
        client = NvidiaClient()
        try:
            response = client.quick_chat(args.model, args.message)
            print(f"回复: {response}")
        except Exception as e:
            print(f"错误: {type(e).__name__}: {e}")
        finally:
            client.close()
    elif args.platform:
        # 指定平台测试
        test_platform(args.platform, verbose=not args.quiet)
    else:
        # 默认测试 NVIDIA 免费模型
        test_nvidia_models(verbose=not args.quiet)