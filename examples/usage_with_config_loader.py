"""
使用 ConfigLoader 的配置示例
展示新 API key 管理系统的使用方法
"""

import os
from src.config_loader import ConfigLoader, get_api_key
from src.platform_registry import registry, use_platform
from src import nvidia_chat, zhipu_chat
from platforms.nvidia.client import NvidiaClient
from platforms.zhipu.client import ZhipuClient


def example_1_direct_api_key():
    """示例1: 直接调用便捷函数，自动从环境变量获取"""
    print("\n=== 示例1: 使用便捷函数（自动加载 .env）===")

    # 先确保已加载环境变量
    ConfigLoader.load_env('.env.local')

    try:
        # 这种方式会自动从环境变量获取 key
        # 无需手动传递 api_key 参数
        result = nvidia_chat("minimax-m2.7", "Hello")
        print(f"✅ 调用成功: {result[:50]}...")
    except ValueError as e:
        print(f"❌ 需要配置 API key: {e}")
    except Exception as e:
        print(f"⚠️  调用失败（正常，如果没有真实 key）: {type(e).__name__}")


def example_2_platform_registry():
    """示例2: 通过平台注册表创建客户端"""
    print("\n=== 示例2: 使用平台注册表 ===")

    ConfigLoader.load_env('.env.local')

    try:
        # 创建智谱客户端（自动加载 ZHIPU_API_KEY）
        client = registry.create_client('zhipu')
        print(f"✅ 创建客户端: {client}")

        # 测试连接
        if client.test_connection():
            print("✅ 连接成功")
        else:
            print("❌ 连接失败")

        client.close()
    except ValueError as e:
        print(f"❌ 需要配置 API key: {e}")
    except Exception as e:
        print(f"⚠️  连接测试失败: {type(e).__name__}")


def example_3_explicit_api_key():
    """示例3: 显式传递 api_key 参数（用于高级用法）"""
    print("\n=== 示例3: 显式传递 api_key ===")

    # 从环境变量或配置文件读取
    api_key = os.getenv("NVIDIA_API_KEY")

    if api_key:
        from platforms.nvidia.client import NvidiaClient
        client = NvidiaClient(api_key=api_key)
        print(f"✅ 使用显式 key 创建客户端: {client}")
        client.close()
    else:
        print("⚠️  未找到 NVIDIA_API_KEY，跳过示例")


def example_4_multi_platform():
    """示例4: 多平台配置验证"""
    print("\n=== 示例4: 验证所有平台配置 ===")

    ConfigLoader.load_env('.env.local')

    results = ConfigLoader.validate_all()
    for platform, is_valid in results.items():
        status = "✅" if is_valid else "❌"
        print(f"  {status} {platform}")

    if any(results.values()):
        print("\n✅ 至少有一个平台已配置（环境变量存在）")
        print("⚠️  注意：如果使用 .env.example 的占位符，API 调用会失败，请填入真实 key")
    else:
        print("\n⚠️  没有平台配置，请先编辑 .env.local")


def main():
    print("=" * 60)
    print("  ConfigLoader 使用示例")
    print("=" * 60)

    # 1. 自动加载 .env.local（如果存在）
    ConfigLoader.load_env()

    # 运行各个示例
    example_1_direct_api_key()
    example_2_platform_registry()
    example_3_explicit_api_key()
    example_4_multi_platform()

    print("\n" + "=" * 60)
    print("  使用总结")
    print("=" * 60)
    print("""
推荐的用法：

1. 项目启动时加载配置：
   ConfigLoader.load_env()  # 自动查找 .env 文件

2. 在代码中获取 API key：
   api_key = get_api_key('nvidia')

3. 创建客户端（完全自动）：
   client = create_client('zhipu')  # 自动从环境变量获取 key

4. 配置文件：
   - .env.example      模板（提交到 git）
   - .env.local        你的个人配置（.gitignore）
   - 系统环境变量     生产环境使用

更多信息请查阅：docs/API_KEY_SETUP.md
    """)


if __name__ == "__main__":
    main()
