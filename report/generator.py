"""
报告生成器
统一生成 Markdown 和 JSON 格式的测试报告
"""

import json
import os
from datetime import datetime
from typing import List

import sys
import os as os_module
sys.path.insert(0, os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__))))
from src.models import TestResult, TestReport


class MarkdownFormatter:
    """Markdown 报告格式化器"""

    TAG_ICONS = {
        'downloadable': '📥',
        'free': '🔓',
        'flash': '⚡',
        'thinking': '🤔',
    }

    def format(self, report: TestReport) -> str:
        """生成 Markdown 格式报告"""
        success_rate = (report.success / report.total * 100) if report.total > 0 else 0

        md = f"""# {report.platform.upper()} 模型批量测试报告

**测试时间**: {report.timestamp}
**平台**: {report.platform}
**总模型数**: {report.total}
**成功率**: {success_rate:.1f}%

---

## 📊 总体统计

| 指标 | 数值 |
|------|------|
| **总模型数** | {report.total} |
| **成功** | {report.success} ✅ |
| **失败** | {report.failed} ❌ |
| **超时** | {report.timeout} ⏰ |
| **成功率** | {success_rate:.1f}% |

---

## 🏆 最快模型排行榜 (Top 10)

| 排名 | 模型ID | 标签 | 响应时间 | 状态 |
|------|--------|------|----------|------|
"""

        successful = sorted(
            [r for r in report.results if r.status == 'success'],
            key=lambda x: x.response_time
        )

        for i, r in enumerate(successful[:10], 1):
            tags_str = self._format_tags(r.tags)
            md += f"| {i} | {r.model_id} | {tags_str} | {r.response_time:.2f}s | ✅ |\n"

        md += """
---

## 🎯 完整测试结果 (按热度排序)

| 热度排名 | 模型ID | 标签 | 响应时间 | 状态/错误 |
|----------|--------|------|----------|----------|
"""

        sorted_results = sorted(report.results, key=lambda x: x.rank)

        for r in sorted_results:
            tags_str = self._format_tags(r.tags)
            if r.status == 'success':
                status_icon = '✅'
                detail = '成功'
            elif r.status == 'timeout':
                status_icon = '⏰'
                detail = '超时'
            else:
                status_icon = '❌'
                detail = r.error_message[:40] if r.error_message else r.status

            md += f"| {r.rank} | {r.model_id} | {tags_str} | {r.response_time:.2f}s | {status_icon} {detail} |\n"

        md += f"""
---

## 📋 标签说明

| 图标 | 标签名 | 含义 |
|------|--------|------|
| 📥 | downloadable | 模型权重可下载 |
| 🔓 | free | 免费API端点 |
| ⚡ | flash | 快速模型 |
| 🤔 | thinking | 推理模型 |

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return md

    def _format_tags(self, tags: List[str]) -> str:
        """格式化标签为图标字符串"""
        if not tags:
            return '-'
        icons = [self.TAG_ICONS.get(t, t) for t in tags]
        return ' '.join(icons)

    def save(self, content: str, filepath: str):
        """保存 Markdown 文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


class JsonFormatter:
    """JSON 报告格式化器"""

    def format(self, report: TestReport) -> str:
        """生成 JSON 格式报告"""
        data = {
            'timestamp': report.timestamp,
            'platform': report.platform,
            'total': report.total,
            'success': report.success,
            'failed': report.failed,
            'timeout': report.timeout,
            'success_rate': round(report.success / report.total * 100, 2) if report.total > 0 else 0,
            'results': [r.to_dict() for r in report.results]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def save(self, content: str, filepath: str):
        """保存 JSON 文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


class ReportGenerator:
    """报告生成器（统一入口）"""

    def __init__(self, platform: str):
        self.platform = platform
        self.md_formatter = MarkdownFormatter()
        self.json_formatter = JsonFormatter()

    def generate(self, results: List[TestResult], output_dir: str = "docs") -> dict:
        """
        生成报告

        Args:
            results: 测试结果列表
            output_dir: 输出目录

        Returns:
            包含文件路径的字典
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        report = TestReport(
            timestamp=datetime.now().isoformat(),
            platform=self.platform,
            total=len(results),
            success=sum(1 for r in results if r.status == 'success'),
            failed=sum(1 for r in results if r.status == 'failed'),
            timeout=sum(1 for r in results if r.status == 'timeout'),
            results=results
        )

        platform_dir = f"{output_dir}/{self.platform}"
        raw_dir = f"{output_dir}/raw-data/{self.platform}"

        md_file = f"{platform_dir}/{self.platform.upper()}_BATCH_TEST_{timestamp}.md"
        json_file = f"{raw_dir}/{self.platform}_raw_{timestamp}.json"

        md_content = self.md_formatter.format(report)
        self.md_formatter.save(md_content, md_file)

        json_content = self.json_formatter.format(report)
        self.json_formatter.save(json_content, json_file)

        return {'markdown': md_file, 'json': json_file}