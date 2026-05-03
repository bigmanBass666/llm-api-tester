"""
全面测试脚本 - 验证重构后的所有模块正常工作
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_module_imports():
    """测试所有关键模块的导入"""
    print("=" * 60)
    print("📦 测试 1: 模块导入验证")
    print("=" * 60)

    modules_to_test = [
        # 核心模块
        ("src.models", ["ModelInfo", "ChatMessage", "TestResult", "TestReport"]),
        ("src.platform_config", ["PlatformConfigLoader", "ScraperConfig", "ClientConfig", "PlatformConfig"]),
        ("src.config_loader", ["ConfigLoader", "get_api_key", "get_free_models"]),
        ("src.platform_registry", ["PlatformRegistry", "register_platform"]),

        # 平台基类
        ("platforms.base.base_client", ["BasePlatformClient"]),
        ("platforms.base.base_scraper", ["BaseScraper"]),

        # NVIDIA 平台
        ("platforms.nvidia.client", ["NvidiaClient"]),
        ("platforms.nvidia.scraper", ["NvidiaScraper"]),

        # 智谱平台
        ("platforms.zhipu.client", ["ZhipuClient"]),
        ("platforms.zhipu.scraper", ["ZhipuScraper"]),

        # 兼容层
        ("crawler.scraper", ["NvidiaScraper", "fix_model_id", "scrape_top_models"]),
    ]

    passed = 0
    failed = 0

    for module_name, expected_classes in modules_to_test:
        try:
            module = __import__(module_name, fromlist=expected_classes)
            missing_classes = []
            for class_name in expected_classes:
                if not hasattr(module, class_name):
                    missing_classes.append(class_name)

            if missing_classes:
                print(f"❌ {module_name}: 缺少类 {missing_classes}")
                failed += 1
            else:
                print(f"✅ {module_name}: 导入成功 ({', '.join(expected_classes[:3])}...)")
                passed += 1

        except ImportError as e:
            print(f"❌ {module_name}: 导入失败 - {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {module_name}: 意外错误 - {e}")
            failed += 1

    print(f"\n📊 模块导入测试结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_nvidia_scraper_instantiation():
    """测试 NVIDIA 爬虫实例化"""
    print("\n" + "=" * 60)
    print("🔍 测试 2: NVIDIA 爬虫实例化和配置加载")
    print("=" * 60)

    try:
        from platforms.nvidia.scraper import NvidiaScraper

        # 测试实例化（不需要浏览器）
        scraper = NvidiaScraper(headless=True)

        # 验证配置已正确加载
        assert hasattr(scraper, '_CONFIG'), "缺少 _CONFIG 属性"
        assert hasattr(scraper, 'SELECTORS'), "缺少 SELECTORS 属性"
        assert hasattr(scraper, 'TEXT_MODEL_CATEGORIES'), "缺少 TEXT_MODEL_CATEGORIES 属性"
        assert hasattr(scraper, 'NON_TEXT_KEYWORDS'), "缺少 NON_TEXT_KEYWORDS 属性"

        # 验证配置值不为空
        assert len(scraper._CONFIG) > 0, "_CONFIG 为空"
        assert len(scraper.SELECTORS) > 0, "SELECTORS 为空"
        assert len(scraper.TEXT_MODEL_CATEGORIES) > 0, "TEXT_MODEL_CATEGORIES 为空"
        assert len(scraper.NON_TEXT_KEYWORDS) > 0, "NON_TEXT_KEYWORDS 为空"

        # 打印配置摘要
        print(f"✅ NvidiaScraper 实例化成功")
        print(f"   - 配置项数: {len(scraper._CONFIG)}")
        print(f"   - 选择器数: {len(scraper.SELECTORS)}")
        print(f"   - 文字模型分类: {len(scraper.TEXT_MODEL_CATEGORIES)} 个")
        print(f"   - 非文字关键词: {len(scraper.NON_TEXT_KEYWORDS)} 个")

        return True

    except Exception as e:
        print(f"❌ NVIDIA 爬虫测试失败: {e}")
        return False


def test_nvidia_client_instantiation():
    """测试 NVIDIA 客户端实例化"""
    print("\n" + "=" * 60)
    print("💬 测试 3: NVIDIA 客户端实例化和配置加载")
    print("=" * 60)

    try:
        from platforms.nvidia.client import NvidiaClient

        # 测试实例化
        client = NvidiaClient(api_key="test-api-key")

        # 验证 FREE_MODELS 已从配置加载
        assert hasattr(client, 'FREE_MODELS'), "缺少 FREE_MODELS 属性"
        assert isinstance(client.FREE_MODELS, dict), "FREE_MODELS 不是字典"
        assert len(client.FREE_MODELS) > 0, "FREE_MODELS 为空"

        # 验证基础 URL 已设置
        assert client.base_url is not None, "base_url 未设置"

        # 打印配置摘要
        print(f"✅ NvidiaClient 实例化成功")
        print(f"   - Base URL: {client.base_url}")
        print(f"   - 免费模型数: {len(client.FREE_MODELS)}")
        print(f"   - 模型示例: {list(client.FREE_MODELS.keys())[:5]}...")

        return True

    except Exception as e:
        print(f"❌ NVIDIA 客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_zhipu_scraper_instantiation():
    """测试智谱爬虫实例化"""
    print("\n" + "=" * 60)
    print("🔍 测试 4: 智谱爬虫实例化和配置加载")
    print("=" * 60)

    try:
        from platforms.zhipu.scraper import ZhipuScraper

        # 测试实例化
        scraper = ZhipuScraper()

        # 验证 KNOWN_MODELS 存在
        assert hasattr(scraper, 'KNOWN_MODELS'), "缺少 KNOWN_MODELS 属性"

        print(f"✅ ZhipuScraper 实例化成功")
        print(f"   - 预定义模型数: {len(scraper.KNOWN_MODELS)}")

        return True

    except Exception as e:
        print(f"❌ 智谱爬虫测试失败: {e}")
        return False


def test_zhipu_client_instantiation():
    """测试智谱客户端实例化"""
    print("\n" + "=" * 60)
    print("💬 测试 5: 智谱客户端实例化")
    print("=" * 60)

    try:
        from platforms.zhipu.client import ZhipuClient

        # 测试实例化
        client = ZhipuClient(api_key="test-api-key")

        print(f"✅ ZhipuClient 实例化成功")
        print(f"   - Base URL: {client.base_url}")

        return True

    except Exception as e:
        print(f"❌ 智谱客户端测试失败: {e}")
        return False


def test_crawler_compatibility_layer():
    """测试兼容层是否正常工作"""
    print("\n" + "=" * 60)
    print("🔄 测试 6: crawler/scraper.py 兼容层验证")
    print("=" * 60)

    try:
        from crawler.scraper import (
            NvidiaScraper,
            fix_model_id,
            TEXT_MODEL_CATEGORIES,
            NON_TEXT_KEYWORDS
        )

        # 测试 fix_model_id 函数
        result = fix_model_id("deepseek-v3_2")
        assert result == "deepseek-v3.2", f"fix_model_id 失败: {result}"

        # 验证配置常量已从 PlatformConfigLoader 加载
        assert TEXT_MODEL_CATEGORIES is not None, "TEXT_MODEL_CATEGORIES 为 None"
        assert NON_TEXT_KEYWORDS is not None, "NON_TEXT_KEYWORDS 为 None"
        assert len(TEXT_MODEL_CATEGORIES) > 0, "TEXT_MODEL_CATEGORIES 为空"
        assert len(NON_TEXT_KEYWORDS) > 0, "NON_TEXT_KEYWORDS 为空"

        print(f"✅ 兼容层验证成功")
        print(f"   - fix_model_id('deepseek-v3_2') = '{result}'")
        print(f"   - TEXT_MODEL_CATEGORIES: {len(TEXT_MODEL_CATEGORIES)} 个分类")
        print(f"   - NON_TEXT_KEYWORDS: {len(NON_TEXT_KEYWORDS)} 个关键词")

        return True

    except ImportError as e:
        print(f"⚠️ 兼容层导入警告: {e}")
        return False
    except Exception as e:
        print(f"❌ 兼容层测试失败: {e}")
        return False


def test_platform_config_loader():
    """测试 PlatformConfigLoader 的核心功能"""
    print("\n" + "=" * 60)
    print("⚙️ 测试 7: PlatformConfigLoader 功能验证")
    print("=" * 60)

    try:
        from src.platform_config import PlatformConfigLoader

        # 重置配置
        PlatformConfigLoader.reload()

        # 测试获取所有平台
        all_platforms = PlatformConfigLoader.get_all_platforms()
        assert len(all_platforms) > 0, "没有找到任何平台"

        # 测试获取可用平台
        available_platforms = PlatformConfigLoader.get_available_platforms()
        assert len(available_platforms) > 0, "没有可用平台"
        assert 'nvidia' in available_platforms, "NVIDIA 不在可用平台列表中"
        assert 'zhipu' in available_platforms, "智谱不在可用平台列表中"

        # 测试获取 NVIDIA 配置
        nvidia_config = PlatformConfigLoader.get_config('nvidia')
        assert nvidia_config is not None, "NVIDIA 配置为空"
        assert nvidia_config.name == 'nvidia'

        # 测试获取 NVIDIA 爬虫配置
        nvidia_scraper_config = PlatformConfigLoader.get_scraper_config('nvidia')
        assert nvidia_scraper_config is not None, "NVIDIA 爬虫配置为空"
        assert nvidia_scraper_config.base_url == 'https://build.nvidia.com'

        # 测试获取 NVIDIA 客户端配置
        nvidia_client_config = PlatformConfigLoader.get_client_config('nvidia')
        assert nvidia_client_config is not None, "NVIDIA 客户端配置为空"
        assert len(nvidia_client_config.free_models) > 0, "免费模型列表为空"

        print(f"✅ PlatformConfigLoader 功能正常")
        print(f"   - 总平台数: {len(all_platforms)}")
        print(f"   - 可用平台: {available_platforms}")
        print(f"   - NVIDIA 爬虫配置: ✓")
        print(f"   - NVIDIA 客户端配置: ✓ (包含 {len(nvidia_client_config.free_models)} 个免费模型)")

        return True

    except Exception as e:
        print(f"❌ PlatformConfigLoader 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("🚀 全面测试开始 - 验证重构后的代码完整性")
    print("=" * 70 + "\n")

    results = []

    # 运行所有测试
    results.append(("模块导入验证", test_module_imports()))
    results.append(("NVIDIA 爬虫实例化", test_nvidia_scraper_instantiation()))
    results.append(("NVIDIA 客户端实例化", test_nvidia_client_instantiation()))
    results.append(("智谱爬虫实例化", test_zhipu_scraper_instantiation()))
    results.append(("智谱客户端实例化", test_zhipu_client_instantiation()))
    results.append(("兼容层验证", test_crawler_compatibility_layer()))
    results.append(("PlatformConfigLoader 功能", test_platform_config_loader()))

    # 生成总结报告
    print("\n" + "=" * 70)
    print("📊 测试总结报告")
    print("=" * 70)

    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    failed_tests = total_tests - passed_tests

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} | {test_name}")

    print("-" * 70)
    success_rate = (passed_tests / total_tests) * 100
    print(f"总计: {total_tests} 项测试 | 通过: {passed_tests} | 失败: {failed_tests} | 成功率: {success_rate:.1f}%")
    print("=" * 70 + "\n")

    if failed_tests == 0:
        print("🎉 所有测试通过！重构完全成功，代码运行正常！\n")
        return 0
    else:
        print(f"⚠️ 有 {failed_tests} 项测试失败，需要检查！\n")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
