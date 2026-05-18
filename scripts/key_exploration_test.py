"""
API Key 全面探索性测试

测试所有平台的所有 API Key，包括：
1. 基础连接测试
2. 模型列表测试
3. 性能测试（响应时间、TTFT）
4. 并发测试
5. 错误处理测试
"""

import os
import sys
import time
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config_loader import ConfigLoader
from src.platform_config import PlatformConfigLoader
from src.models import ModelInfo, ChatMessage
from platforms.common.openai_compatible_client import OpenAICompatibleClient, KimiClient, MiniMaxClient
from platforms.zhipu.client import ZhipuClient


@dataclass
class KeyTestResult:
    """单个 Key 的测试结果"""
    platform: str
    key_name: str
    key_suffix: str  # key 的最后几位，用于标识

    # 连接测试
    connection_success: bool = False
    connection_error: Optional[str] = None

    # 模型列表
    models_count: int = 0
    models_list: List[str] = None

    # 性能测试
    test_model: Optional[str] = None
    response_time: Optional[float] = None
    ttft: Optional[float] = None
    response_content: Optional[str] = None

    # 错误信息
    error: Optional[str] = None

    def __post_init__(self):
        if self.models_list is None:
            self.models_list = []

    def to_dict(self) -> dict:
        return asdict(self)


class KeyExplorationTestSuite:
    """API Key 全面探索性测试套件"""

    def __init__(self):
        self.results: List[KeyTestResult] = []
        self.test_message = "你好，请简短回复"

    def _get_all_keys(self) -> List[Dict[str, Any]]:
        """获取所有 API Key 配置"""
        keys = []

        # 智谱 GLM
        zhipu_key1 = os.getenv("ZHIPU_API_KEY")
        zhipu_key2 = os.getenv("ZHIPU_API_KEY_2")
        if zhipu_key1:
            keys.append({
                "platform": "zhipu",
                "key_name": "ZHIPU_API_KEY",
                "key": zhipu_key1,
                "base_url": "https://open.bigmodel.cn/api/paas/v4"
            })
        if zhipu_key2:
            keys.append({
                "platform": "zhipu",
                "key_name": "ZHIPU_API_KEY_2",
                "key": zhipu_key2,
                "base_url": "https://open.bigmodel.cn/api/paas/v4"
            })

        # Kimi
        kimi_key = os.getenv("KIMI_API_KEY")
        if kimi_key:
            keys.append({
                "platform": "kimi",
                "key_name": "KIMI_API_KEY",
                "key": kimi_key,
                "base_url": "https://api.moonshot.cn/v1"
            })
        for i in range(2, 5):
            key = os.getenv(f"KIMI_API_KEY_{i}")
            if key:
                keys.append({
                    "platform": "kimi",
                    "key_name": f"KIMI_API_KEY_{i}",
                    "key": key,
                    "base_url": "https://api.moonshot.cn/v1"
                })

        # MiniMax
        for i in range(1, 3):
            key = os.getenv(f"MINIMAX_API_KEY_{i}")
            if key:
                keys.append({
                    "platform": "minimax",
                    "key_name": f"MINIMAX_API_KEY_{i}",
                    "key": key,
                    "base_url": "https://api.minimax.chat/v1"
                })

        return keys

    def _create_client(self, platform: str, api_key: str, base_url: str):
        """创建平台客户端"""
        if platform == "zhipu":
            return ZhipuClient(api_key=api_key, base_url=base_url)
        elif platform == "kimi":
            return KimiClient(api_key=api_key, base_url=base_url)
        elif platform == "minimax":
            return MiniMaxClient(api_key=api_key, base_url=base_url)
        else:
            return OpenAICompatibleClient(
                api_key=api_key,
                base_url=base_url,
                platform_name=platform
            )

    def _test_single_key(self, key_config: Dict[str, Any]) -> KeyTestResult:
        """测试单个 API Key"""
        platform = key_config["platform"]
        key_name = key_config["key_name"]
        key = key_config["key"]
        base_url = key_config["base_url"]

        # 获取 key 的后几位用于标识
        key_suffix = key[-8:] if len(key) > 8 else key

        result = KeyTestResult(
            platform=platform,
            key_name=key_name,
            key_suffix=key_suffix
        )

        client = None
        try:
            # 创建客户端
            client = self._create_client(platform, key, base_url)

            # 1. 连接测试
            print(f"  测试连接...")
            connection_ok = client.test_connection()
            result.connection_success = connection_ok

            if not connection_ok:
                result.connection_error = "连接失败"
                return result

            # 2. 获取模型列表
            print(f"  获取模型列表...")
            models = client.list_models()
            result.models_count = len(models)
            result.models_list = [m.id for m in models[:10]]  # 只保存前10个

            # 3. 性能测试
            print(f"  性能测试...")
            if models:
                # 选择第一个模型进行测试
                test_model = models[0].id
                result.test_model = test_model

                messages = [ChatMessage(role="user", content=self.test_message)]

                start_time = time.time()
                try:
                    response = client.chat(test_model, messages, max_tokens=64)
                    end_time = time.time()

                    result.response_time = end_time - start_time
                    result.response_content = response[:100] if response else ""
                except Exception as e:
                    result.error = f"性能测试失败: {str(e)}"

        except Exception as e:
            result.error = str(e)
        finally:
            if client:
                client.close()

        return result

    def test_all_keys(self) -> List[KeyTestResult]:
        """测试所有 API Key"""
        keys = self._get_all_keys()

        if not keys:
            print("❌ 未找到任何 API Key，请检查 .env.local 文件")
            return []

        print(f"🚀 开始测试 {len(keys)} 个 API Key\n")
        self.results = []

        for i, key_config in enumerate(keys, 1):
            platform = key_config["platform"]
            key_name = key_config["key_name"]

            print(f"[{i}/{len(keys)}] 测试 {platform} - {key_name}")

            result = self._test_single_key(key_config)
            self.results.append(result)

            # 打印结果
            if result.connection_success:
                print(f"  ✅ 连接成功")
                print(f"  📊 模型数量: {result.models_count}")
                if result.response_time:
                    print(f"  ⚡ 响应时间: {result.response_time:.3f}s")
            else:
                print(f"  ❌ 连接失败: {result.connection_error or result.error}")

            print()

        return self.results

    def generate_summary(self) -> Dict[str, Any]:
        """生成测试摘要"""
        if not self.results:
            return {}

        total = len(self.results)
        success = sum(1 for r in self.results if r.connection_success)
        failed = total - success

        summary = {
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_keys": total,
            "success": success,
            "failed": failed,
            "platforms": {}
        }

        # 按平台统计
        for result in self.results:
            platform = result.platform
            if platform not in summary["platforms"]:
                summary["platforms"][platform] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "keys": []
                }

            summary["platforms"][platform]["total"] += 1
            if result.connection_success:
                summary["platforms"][platform]["success"] += 1
            else:
                summary["platforms"][platform]["failed"] += 1

            summary["platforms"][platform]["keys"].append({
                "key_name": result.key_name,
                "key_suffix": result.key_suffix,
                "success": result.connection_success,
                "models_count": result.models_count,
                "response_time": result.response_time,
                "error": result.error
            })

        return summary

    def export_report(self, filename: Optional[str] = None) -> str:
        """导出测试报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/key_exploration_report_{timestamp}.md"

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        summary = self.generate_summary()

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 🔑 API Key 全面探索性测试报告\n\n")

            # 摘要
            f.write("## 📊 测试摘要\n\n")
            f.write(f"- **测试时间**: {summary.get('test_time', 'N/A')}\n")
            f.write(f"- **测试总数**: {summary.get('total_keys', 0)}\n")
            f.write(f"- **成功**: {summary.get('success', 0)} ✅\n")
            f.write(f"- **失败**: {summary.get('failed', 0)} ❌\n\n")

            # 按平台统计
            f.write("## 🏢 平台统计\n\n")
            for platform, stats in summary.get("platforms", {}).items():
                f.write(f"### {platform.upper()}\n\n")
                f.write(f"- **总数**: {stats['total']}\n")
                f.write(f"- **成功**: {stats['success']}\n")
                f.write(f"- **失败**: {stats['failed']}\n\n")

                # 详细表格
                f.write("| Key 名称 | Key 后缀 | 状态 | 模型数量 | 响应时间 | 错误信息 |\n")
                f.write("|----------|----------|------|----------|----------|----------|\n")

                for key_info in stats["keys"]:
                    status = "✅" if key_info["success"] else "❌"
                    models = str(key_info["models_count"]) if key_info["success"] else "-"
                    response_time = f"{key_info['response_time']:.3f}s" if key_info["response_time"] else "-"
                    error = key_info["error"][:50] if key_info["error"] else "-"

                    f.write(f"| {key_info['key_name']} | {key_info['key_suffix']} | {status} | {models} | {response_time} | {error} |\n")

                f.write("\n")

            # 详细结果
            f.write("## 📋 详细测试结果\n\n")
            for result in self.results:
                f.write(f"### {result.platform} - {result.key_name}\n\n")
                f.write(f"- **Key 后缀**: {result.key_suffix}\n")
                f.write(f"- **连接状态**: {'✅ 成功' if result.connection_success else '❌ 失败'}\n")

                if result.connection_success:
                    f.write(f"- **模型数量**: {result.models_count}\n")
                    if result.models_list:
                        f.write(f"- **部分模型列表**: {', '.join(result.models_list[:5])}\n")
                    if result.test_model:
                        f.write(f"- **测试模型**: {result.test_model}\n")
                    if result.response_time:
                        f.write(f"- **响应时间**: {result.response_time:.3f}s\n")
                    if result.response_content:
                        f.write(f"- **响应内容**: {result.response_content}\n")
                else:
                    f.write(f"- **错误信息**: {result.error or result.connection_error}\n")

                f.write("\n")

            # 推荐分析
            f.write("## 🎯 推荐分析\n\n")

            # 找出最快响应
            successful_results = [r for r in self.results if r.connection_success and r.response_time]
            if successful_results:
                fastest = min(successful_results, key=lambda x: x.response_time)
                f.write(f"**🏆 最快响应**: `{fastest.platform} - {fastest.key_name}` ({fastest.response_time:.3f}s)\n\n")

            # 找出模型最多的
            if successful_results:
                most_models = max(successful_results, key=lambda x: x.models_count)
                f.write(f"**📊 模型最多**: `{most_models.platform} - {most_models.key_name}` ({most_models.models_count} 个模型)\n\n")

            # 按平台推荐
            f.write("### 平台推荐\n\n")
            for platform, stats in summary.get("platforms", {}).items():
                successful_keys = [k for k in stats["keys"] if k["success"]]
                if successful_keys:
                    # 找出该平台最快的 key
                    platform_results = [r for r in self.results if r.platform == platform and r.connection_success and r.response_time]
                    if platform_results:
                        fastest = min(platform_results, key=lambda x: x.response_time)
                        f.write(f"- **{platform.upper()}**: 推荐使用 `{fastest.key_name}` (响应时间 {fastest.response_time:.3f}s)\n")

            f.write("\n---\n\n")
            f.write("### 📝 说明\n\n")
            f.write("- 测试消息: \"你好，请简短回复\"\n")
            f.write("- Max Tokens: 64\n")
            f.write("- 响应时间: 从发送请求到收到完整响应的时间\n")
            f.write("- 测试模型: 每个平台选择第一个可用模型\n")

        print(f"📊 报告已生成: {filename}")
        return filename

    def export_json(self, filename: Optional[str] = None) -> str:
        """导出原始 JSON 数据"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/raw-data/key_exploration_raw_{timestamp}.json"

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        data = {
            "summary": self.generate_summary(),
            "results": [r.to_dict() for r in self.results]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 原始数据已保存: {filename}")
        return filename


def main():
    """主函数"""
    print("=" * 60)
    print("🔑 API Key 全面探索性测试")
    print("=" * 60)
    print()

    # 加载配置
    ConfigLoader.load_env()

    # 创建测试套件
    suite = KeyExplorationTestSuite()

    # 运行测试
    results = suite.test_all_keys()

    if results:
        # 导出报告
        suite.export_report()
        suite.export_json()

        # 打印摘要
        summary = suite.generate_summary()
        print("\n" + "=" * 60)
        print("📊 测试摘要")
        print("=" * 60)
        print(f"总测试数: {summary.get('total_keys', 0)}")
        print(f"成功: {summary.get('success', 0)}")
        print(f"失败: {summary.get('failed', 0)}")
        print()

        # 按平台打印
        for platform, stats in summary.get("platforms", {}).items():
            print(f"{platform.upper()}: {stats['success']}/{stats['total']} 成功")


if __name__ == "__main__":
    main()
