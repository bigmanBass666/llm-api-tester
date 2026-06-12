"""
单元测试：验证 speed_tester 框架的核心逻辑
"""

import json
import tempfile
from pathlib import Path

# 添加项目根目录到路径

from crawler.speed_tester import SpeedTestResult, BaseSpeedTestSuite

def test_speed_test_result():
    """测试 SpeedTestResult 数据类"""
    print("🧪 测试 SpeedTestResult...")

    # 创建成功结果
    result = SpeedTestResult(
        model_id="test-model",
        platform="test",
        test_message="test",
        timestamp="2026-04-18 00:00:00",
        ttft=0.5,
        total_time=1.0,
        first_chunk="Hello",
        concurrency=10,
        is_free=True,
        category="通用"
    )

    assert result.is_success() is True
    assert result.supports_streaming() is True
    assert result.concurrency == 10
    assert result.get_value_for_ranking() == 1.0

    # 创建失败结果
    failed = SpeedTestResult(
        model_id="fail-model",
        platform="test",
        test_message="test",
        timestamp="2026-04-18 00:00:00",
        error="Test error"
    )
    assert failed.is_success() is False
    assert failed.supports_streaming() is False
    assert failed.get_value_for_ranking() == float('inf')

    print("   ✅ SpeedTestResult 基本功能正常")
    print("   ✅ 成功/失败判断正确")
    print("   ✅ 流式支持检测正确")
    print("   ✅ 排序值计算正确")

def test_summary_generation():
    """测试摘要统计逻辑"""
    print("\n🧪 测试摘要统计生成...")

    # 创建模拟套件
    class DummySuite(BaseSpeedTestSuite):
        def _create_client(self):
            return None
        def _list_models(self):
            return []
        def _test_single_model(self, *args):
            return SpeedTestResult("test", "test", "test", "2026-04-18 00:00:00")

    suite = DummySuite()

    # 注入测试数据
    suite.results = [
        SpeedTestResult("m1", "zhipu", "test", "2026-04-18 00:00:00",
                       ttft=0.5, total_time=1.0, concurrency=10),
        SpeedTestResult("m2", "zhipu", "test", "2026-04-18 00:00:00",
                       ttft=1.0, total_time=2.0, concurrency=20),
        SpeedTestResult("m3", "zhipu", "test", "2026-04-18 00:00:00",
                       ttft=2.0, total_time=4.0, concurrency=200),
        SpeedTestResult("m4", "zhipu", "test", "2026-04-18 00:00:00",
                       error="Timeout"),  # 失败的模型
    ]

    summary = suite.generate_summary()

    assert summary["total"] == 4
    assert summary["success"] == 3
    assert summary["failed"] == 1
    assert summary["streaming_supported"] == 3
    assert summary["ttft_min"] == 0.5
    assert summary["ttft_max"] == 2.0
    assert abs(summary["ttft_avg"] - 1.1666666666666667) < 0.001
    assert summary["concurrency_min"] == 10
    assert summary["concurrency_max"] == 200
    assert summary["concurrency_avg"] == 76.66666666666667

    # 检查性价比排名
    assert len(summary["top_by_efficiency"]) == 3
    # m3: 200/2.0 = 100, m2: 20/1.0 = 20, m1: 10/0.5 = 20 -> m3第一
    assert summary["top_by_efficiency"][0]["model"] == "m3"

    print("   ✅ 统计计算正确")
    print("   ✅ 并发数分析正确")
    print("   ✅ 性价比排名正确")

def test_markdown_export():
    """测试 Markdown 报告生成"""
    print("\n🧪 测试 Markdown 报告导出...")

    class DummySuite(BaseSpeedTestSuite):
        def _create_client(self):
            return None
        def _list_models(self):
            return []
        def _test_single_model(self, *args):
            return SpeedTestResult("test", "test", "test", "2026-04-18 00:00:00")

    suite = DummySuite(output_dir=tempfile.mkdtemp())
    suite.results = [
        SpeedTestResult("fast-model", "zhipu", "test", "2026-04-18 00:00:00",
                       ttft=0.5, total_time=1.0, concurrency=100, category="通用"),
        SpeedTestResult("slow-model", "zhipu", "test", "2026-04-18 00:00:00",
                       ttft=2.0, total_time=5.0, concurrency=10, category="视觉"),
        SpeedTestResult("fail-model", "zhipu", "test", "2026-04-18 00:00:00",
                       error="Test error"),
    ]

    md_file = suite.export_markdown()
    assert Path(md_file).exists()

    content = Path(md_file).read_text(encoding='utf-8')
    assert "AI 模型响应速度测试报告" in content
    assert "TTFT" in content
    assert "fast-model" in content
    assert "slow-model" in content
    assert "fail-model" in content
    assert "效率指数" in content or "性价比" in content
    assert "并发" in content

    print(f"   ✅ Markdown 报告生成成功: {md_file}")
    print(f"   ✅ 报告包含分析内容 (大小: {len(content)} bytes)")

def test_json_export():
    """测试 JSON 原始数据导出"""
    print("\n🧪 测试 JSON 原始数据导出...")

    class DummySuite(BaseSpeedTestSuite):
        def _create_client(self):
            return None
        def _list_models(self):
            return []
        def _test_single_model(self, *args):
            return SpeedTestResult("test", "test", "test", "2026-04-18 00:00:00")

    suite = DummySuite(output_dir=tempfile.mkdtemp())
    suite.results = [
        SpeedTestResult("model1", "zhipu", "test", "2026-04-18 00:00:00",
                       ttft=0.5, total_time=1.0, concurrency=10),
    ]

    json_file = suite.export_json()
    assert Path(json_file).exists()

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert "summary" in data
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["model_id"] == "model1"
    assert data["summary"]["total"] == 1

    print(f"   ✅ JSON 原始数据导出成功: {json_file}")
    print(f"   ✅ 数据结构正确")

if __name__ == "__main__":
    print("="*60)
    print("🧪 开始单元测试: speed_tester 框架")
    print("="*60)

    try:
        test_speed_test_result()
        test_summary_generation()
        test_markdown_export()
        test_json_export()

        print("\n" + "="*60)
        print("✅ 所有单元测试通过!")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        raise
