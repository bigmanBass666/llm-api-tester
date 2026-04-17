#!/usr/bin/env python3
"""
快速环境配置脚本
使用说明：
    python scripts/setup_env.py
"""

import os
import sys
from pathlib import Path

def create_env_local():
    """创建 .env.local 文件"""
    env_example = Path('.env.example')
    env_local = Path('.env.local')

    if not env_example.exists():
        print("❌ 错误：.env.example 文件不存在")
        return False

    if env_local.exists():
        response = input("⚠️  .env.local 已存在，是否覆盖？(y/N): ")
        if response.lower() != 'y':
            print("取消操作")
            return False

    # 复制模板
    content = env_example.read_text()
    env_local.write_text(content)

    print(f"✅ 已创建 .env.local")
    print(f"📝 请编辑 {env_local} 填入真实 API keys")
    return True


def verify_config():
    """验证配置是否正常"""
    print("🔍 验证配置...")

    # 检查 .env.local 是否存在
    if not Path('.env.local').exists():
        print("❌ .env.local 不存在，请先运行 'python scripts/setup_env.py'")
        return False

    try:
        # 导入配置加载器
        from src.config_loader import ConfigLoader

        # 加载环境变量
        ConfigLoader.load_env('.env.local')

        # 检查各平台配置
        from src.platform_registry import PlatformRegistry
        registry = PlatformRegistry._instance

        if not registry:
            print("❌ 平台注册表未初始化，请先导入客户端模块")
            print("   执行: python -c 'from src import nvidia_client, zhipu_client'")
            return False

        print("✅ 配置加载成功")

        # 验证配置
        results = ConfigLoader.validate_all()
        for platform, valid in results.items():
            if valid:
                print(f"  ✅ {platform}: 已配置")
            else:
                print(f"  ❌ {platform}: 未配置 API key")

        return any(results.values())

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("  API 测试项目 - 环境配置向导")
    print("=" * 60)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_config()
        return

    print("此脚本将帮助您完成初始配置：")
    print("1. 创建 .env.local 配置文件（基于 .env.example）")
    print("2. 指导您填入 API keys")
    print()

    response = input("是否开始配置？(Y/n): ").strip().lower()
    if response and response != 'y':
        print("取消配置")
        return

    print()
    print("步骤 1: 创建 .env.local")
    print("-" * 60)

    if create_env_local():
        print()
        print("步骤 2: 配置 API keys")
        print("-" * 60)
        print("请用文本编辑器打开 .env.local，填入以下内容：")
        print()
        print("  NVIDIA_API_KEY=nvapi-xxxxxxxx")
        print("  ZHIPU_API_KEY=508431.xxxxx")
        print()
        print("获取地址：")
        print("  NVIDIA: https://build.nvidia.com → API Key")
        print("  智谱: https://www.bigmodel.cn/usercenter/proj-mgmt/rate-limits")
        print()
        print("步骤 3: 验证配置")
        print("-" * 60)
        print("运行验证命令：")
        print("  python scripts/setup_env.py --verify")
        print()
        print("✅ 配置完成！")


if __name__ == '__main__':
    main()
