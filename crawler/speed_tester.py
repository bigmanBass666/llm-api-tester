"""
通用速度测试框架

提供统一的接口来测试各种AI模型的响应速度（TTFT、总耗时等）。
支持流式/非流式调用自动检测和降级。
"""

import os
import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Any, Dict


@dataclass
class SpeedTestResult:
    """速度测试结果"""
    model_id: str
    platform: str
    test_message: str
    timestamp: str

    # 流式指标
    ttft: Optional[float] = None  # Time To First Token (秒)
    first_chunk: Optional[str] = None  # 首个chunk内容

    # 整体指标
    total_time: Optional[float] = None  # 总耗时
    full_response: Optional[str] = None  # 完整响应（如适用）

    # 元数据
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

    # 扩展信息（可从外部配置注入）
    concurrency: Optional[int] = None  # 并发限制
    is_free: bool = False  # 是否免费
    category: Optional[str] = None  # 模型分类
    tags: List[str] = None  # 标签

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    def is_success(self) -> bool:
        """是否测试成功"""
        return self.error is None and self.total_time is not None

    def supports_streaming(self) -> bool:
        """是否支持流式（TTFT有效）"""
        return self.ttft is not None

    def get_value_for_ranking(self) -> float:
        """获取用于排名的值（越小越好）"""
        return self.total_time if self.total_time is not None else float('inf')


class BaseSpeedTestSuite(ABC):
    """速度测试套件基类

    子类需要实现:
    - _create_client: 创建平台客户端
    - _list_models: 列出要测试的模型
    - _test_single_model: 测试单个模型
    """

    def __init__(self, output_dir: str = "docs"):
        self.output_dir = output_dir
        self.results: List[SpeedTestResult] = []

    @abstractmethod
    def _create_client(self):
        """创建平台客户端"""
        pass

    @abstractmethod
    def _list_models(self) -> List[dict]:
        """列出要测试的模型列表

        Returns:
            [{"id": "model-id", "name": "Model Name", "tags": []}, ...]
        """
        pass

    def get_model_metadata(self, model_id: str) -> dict:
        """获取模型的额外元数据（如并发数、分类等）

        子类可以重写此方法以提供更多信息。
        默认返回空字典。
        """
        return {}

    @abstractmethod
    def _test_single_model(self, client, model_info: dict,
                          test_message: str, max_tokens: int) -> SpeedTestResult:
        """测试单个模型（子类实现具体逻辑）"""
        pass

    def test_all(self, test_message: str = "回复 OK",
                 max_tokens: int = 64, concurrency: int = 1,
                 platforms: Optional[List[str]] = None) -> List[SpeedTestResult]:
        """
        测试所有模型

        Args:
            test_message: 测试消息
            max_tokens: 最大生成token数
            concurrency: 并发数（暂未实现）
            platforms: 平台过滤列表

        Returns:
            测试结果列表
        """
        client = self._create_client()
        models = self._list_models()

        if platforms:
            models = [m for m in models if m.get("platform") in platforms]

        print(f"开始测试 {len(models)} 个模型...\n")
        self.results = []

        for model_info in models:
            model_id = model_info["id"]
            try:
                result = self._test_single_model(
                    client, model_info, test_message, max_tokens
                )

                # 补充元数据
                metadata = self.get_model_metadata(model_id)
                result.concurrency = metadata.get("concurrency")
                result.is_free = metadata.get("is_free", False)
                result.category = metadata.get("category")
                if metadata.get("tags"):
                    result.tags = metadata["tags"]

                self.results.append(result)

                # 打印进度
                if result.is_success():
                    ttft_str = f"{result.ttft:.3f}s" if result.ttft else "N/A"
                    concur_str = f", 并发 {result.concurrency}" if result.concurrency else ""
                    print(f"✅ {model_id}: TTFT {ttft_str}, total {result.total_time:.3f}s{concur_str}")
                else:
                    print(f"❌ {model_id}: {result.error}")

            except Exception as e:
                result = SpeedTestResult(
                    model_id=model_id,
                    platform=model_info.get("platform", "unknown"),
                    test_message=test_message,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    error=str(e),
                    error_type=type(e).__name__
                )
                self.results.append(result)
                print(f"❌ {model_id}: {e}")

        if hasattr(client, 'close'):
            client.close()

        return self.results

    def generate_summary(self) -> dict:
        """生成测试摘要统计"""
        if not self.results:
            return {}

        success_results = [r for r in self.results if r.is_success()]
        streaming_results = [r for r in success_results if r.supports_streaming()]

        summary = {
            "total": len(self.results),
            "success": len(success_results),
            "failed": len(self.results) - len(success_results),
            "streaming_supported": len(streaming_results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        if streaming_results:
            ttfts = [r.ttft for r in streaming_results if r.ttft]
            if ttfts:
                summary.update({
                    "ttft_min": min(ttfts),
                    "ttft_max": max(ttfts),
                    "ttft_avg": sum(ttfts) / len(ttfts),
                    "ttft_median": sorted(ttfts)[len(ttfts)//2]
                })
            totals = [r.total_time for r in success_results if r.total_time]
            if totals:
                summary.update({
                    "total_min": min(totals),
                    "total_max": max(totals),
                    "total_avg": sum(totals) / len(totals),
                    "total_median": sorted(totals)[len(totals)//2]
                })

        # 并发数分析（仅限有并发数的模型）
        concur_results = [r for r in success_results if r.concurrency is not None]
        if concur_results:
            concur_vals = [r.concurrency for r in concur_results]
            summary.update({
                "concurrency_min": min(concur_vals),
                "concurrency_max": max(concur_vals),
                "concurrency_avg": sum(concur_vals) / len(concur_vals)
            })

            # 性价比分析：并发数 / TTFT（值越高，单位时间内可处理请求越多）
            efficiency_scores = []
            for r in concur_results:
                if r.ttft and r.ttft > 0:
                    score = r.concurrency / r.ttft
                    efficiency_scores.append((r.model_id, score))
            if efficiency_scores:
                efficiency_scores.sort(key=lambda x: x[1], reverse=True)
                summary["top_by_efficiency"] = [
                    {"model": m, "efficiency_score": round(s, 2)}
                    for m, s in efficiency_scores[:5]
                ]

        return summary

    def export_markdown(self, filename: Optional[str] = None) -> str:
        """导出Markdown报告"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/speed_test_report_{timestamp}.md"

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w', encoding='utf-8') as f:
            # 标题
            f.write("# 🚀 AI 模型响应速度测试报告\n\n")

            # 摘要
            summary = self.generate_summary()
            f.write("## 📊 测试摘要\n\n")
            f.write(f"- **测试时间**: {summary.get('timestamp', 'N/A')}\n")
            f.write(f"- **模型总数**: {summary.get('total', 0)}\n")
            f.write(f"- **成功**: {summary.get('success', 0)} ✅\n")
            f.write(f"- **失败**: {summary.get('failed', 0)} ❌\n")
            f.write(f"- **支持流式**: {summary.get('streaming_supported', 0)} 🌊\n\n")

            # 响应速度统计
            if 'ttft_avg' in summary:
                f.write("### ⚡ 响应速度统计（仅流式模型）\n\n")
                f.write(f"- **平均 TTFT**: {summary['ttft_avg']:.3f}s\n")
                f.write(f"- **最快 TTFT**: {summary['ttft_min']:.3f}s\n")
                f.write(f"- **最慢 TTFT**: {summary['ttft_max']:.3f}s\n")
                f.write(f"- **中位数 TTFT**: {summary['ttft_median']:.3f}s\n\n")

            # 并发数统计
            if 'concurrency_avg' in summary:
                f.write("### 🔄 并发限制统计\n\n")
                f.write(f"- **平均并发**: {summary['concurrency_avg']:.1f}\n")
                f.write(f"- **最高并发**: {summary['concurrency_max']}\n")
                f.write(f"- **最低并发**: {summary['concurrency_min']}\n\n")

            # 性价比排名
            if summary.get('top_by_efficiency'):
                f.write("### 💰 性价比排名（并发数/TTFT 越高越好）\n\n")
                f.write("| 排名 | 模型 | 效率指数 |\n")
                f.write("|------|------|----------|\n")
                for i, item in enumerate(summary['top_by_efficiency'], 1):
                    f.write(f"| {i} | {item['model']} | {item['efficiency_score']:.2f} |\n")
                f.write("\n")

            # 详细表格
            f.write("## 🏆 详细结果（按总耗时排序）\n\n")
            headers = ["排名", "模型", "平台", "并发", "TTFT", "总耗时", "首段输出", "状态"]
            if any(r.category for r in self.results):
                headers.insert(3, "分类")
            f.write("| " + " | ".join(headers) + " |\n")
            f.write("|" + "|".join(["---"] * len(headers)) + "|\n")

            # 排序：成功且总耗时最小的在前
            sorted_results = sorted(
                [r for r in self.results if r.is_success()],
                key=lambda x: x.get_value_for_ranking()
            )

            # 失败的排在后面
            failed_results = [r for r in self.results if not r.is_success()]

            rank = 1
            for r in sorted_results:
                ttft_str = f"{r.ttft:.3f}s" if r.ttft else "N/A"
                total_str = f"{r.total_time:.3f}s"
                concur_str = str(r.concurrency) if r.concurrency else "-"
                first = (r.first_chunk or "")[:40].replace("|", "\\|")
                platform = r.platform
                category = r.category or ""

                row = [
                    str(rank), r.model_id, platform, concur_str,
                    ttft_str, total_str, first, "✅"
                ]
                if category:
                    row.insert(3, category)

                f.write("| " + " | ".join(row) + " |\n")
                rank += 1

            for r in failed_results:
                error = (r.error or "Unknown")[:60].replace("|", "\\|")
                row = [
                    "-", r.model_id, r.platform, "-", "-", "-", "-", f"❌ {error}"
                ]
                if any(r.category for r in self.results):
                    row.insert(3, r.category or "")
                f.write("| " + " | ".join(row) + " |\n")

            f.write("\n---\n\n")
            f.write("### 📝 说明\n\n")
            f.write("- **TTFT**: Time To First Token（首字响应时间），仅对流式支持模型测量\n")
            f.write("- **并发**: 模型的速率限制并发数（来源于平台配置）\n")
            f.write("- **效率指数**: `并发数 / TTFT`，表示单位时间内可完成的并发请求数，越高越好\n")
            f.write("- 测试消息: \"回复 OK\"\n")
            f.write(f"- Max Tokens: 64\n")
            f.write("- 测试条件: 单并发，避免相互影响\n")

            # 推荐模型分析
            if len(sorted_results) >= 3:
                f.write("\n### 🎯 推荐分析\n\n")
                fastest = sorted_results[0]
                high_concurs = [r for r in sorted_results if r.concurrency and r.concurrency >= 10]
                if high_concurs:
                    best_balance = min(high_concurs, key=lambda x: x.total_time or float('inf'))
                    f.write(f"**🏆 最快响应**: `{fastest.model_id}` ({fastest.total_time:.3f}s)\n\n")
                    f.write(f"**⚡ 高并发首选**: `{best_balance.model_id}` (并发 {best_balance.concurrency}, 耗时 {best_balance.total_time:.3f}s)\n\n")

                if summary.get('top_by_efficiency'):
                    top_eff = summary['top_by_efficiency'][0]
                    f.write(f"**💰 性价比最优**: `{top_eff['model']}` (效率指数 {top_eff['efficiency_score']:.2f})\n")

        print(f"📊 报告已生成: {filename}")
        return filename

    def export_json(self, filename: Optional[str] = None) -> str:
        """导出原始JSON数据"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/raw-data/speed_test_raw_{timestamp}.json"

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

    def export_all(self, test_name: str = "speed_test"):
        """导出所有格式的报告"""
        import os

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/raw-data", exist_ok=True)

        # 导出
        md_file = self.export_markdown(f"{self.output_dir}/{test_name}_{timestamp}.md")
        json_file = self.export_json(f"{self.output_dir}/raw-data/{test_name}_raw_{timestamp}.json")

        return md_file, json_file


def run_speed_test(suite_class, **kwargs):
    """
    运行速度测试的便捷函数

    Args:
        suite_class: SpeedTestSuite子类
        **kwargs: 传递给测试套件的参数
    """
    suite = suite_class()
    results = suite.test_all(**kwargs)
    suite.export_all()
    return suite
