"""
报告生成器
统一生成 Markdown 和 JSON 格式的测试报告
"""

import json
import os
from datetime import datetime
from typing import List, Optional

from src.models import TestResult, TestReport

# ── 模块级常量 ──────────────────────────────────────

TAG_ICONS = {
    "downloadable": "📥",
    "free": "🔓",
    "flash": "⚡",
    "thinking": "🤔",
    "partner": "🤝",
}

TAG_LEGEND = """
| 图标 | 标签名 | 含义 |
|------|--------|------|
| 📥 | downloadable | 模型权重可下载 |
| 🔓 | free | 免费API端点 |
| ⚡ | flash | 快速模型 |
| 🤔 | thinking | 推理模型 |
| 🤝 | partner | 合作伙伴端点（非免费） |
| ⚠️ | 弃用 | 模型即将弃用 |
| ⏭️ | skipped | 测试已跳过 |
"""


def _format_tags(tags: List[str]) -> str:
    """格式化标签为图标字符串"""
    if not tags:
        return '-'
    return ' '.join(TAG_ICONS.get(t, t) for t in tags)


def _get_scraped_field(result: 'TestResult', field: str):
    """从 TestResult 获取爬虫元数据字段"""
    if result.scraped is not None:
        val = getattr(result.scraped, field, None)
        if val is not None and val != "":
            return val
    return getattr(result, field, None)


class MarkdownFormatter:
    """Markdown 报告格式化器"""

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

| 排名 | 模型ID | 端点 | 调用量 | 发布时间 | 响应时间 | 状态 |
|------|--------|------|--------|----------|----------|------|
"""

        successful = sorted(
            [r for r in report.results if r.status == 'success'],
            key=lambda x: x.response_time
        )

        for i, r in enumerate(successful[:10], 1):
            cv = _get_scraped_field(r, 'call_volume') or ""
            cv = cv.split(" ")[0] if cv and "API calls" in cv else cv or "-"
            pub = _get_scraped_field(r, 'published_at') or "-"
            ep = _get_scraped_field(r, 'endpoint_type') or "unknown"
            ep = '🔓' if ep == 'free' else '🤝' if ep == 'partner' else ep
            depr = _get_scraped_field(r, 'deprecation_info') or ""
            model_id_str = f'{r.model_id} ⚠️' if depr else r.model_id
            md += f"| {i} | {model_id_str} | {ep} | {cv} | {pub} | {r.response_time:.2f}s | ✅ |\n"

        md += """
---

## 🎯 文本模型测试结果 (按热度排序)

| 热度排名 | 模型ID | 端点 | 调用量 | 发布时间 | 标签 | 响应时间 | 状态/错误 |
|----------|--------|------|--------|----------|------|----------|----------|
"""
        sorted_results = sorted(report.results, key=lambda x: x.rank)
        text_results = [r for r in sorted_results if r.model_type not in ('image_generation', 'image_editing')]
        image_results = [r for r in sorted_results if r.model_type in ('image_generation', 'image_editing')]

        for r in text_results:
            tags_str = _format_tags(r.tags)
            cv = _get_scraped_field(r, 'call_volume') or ""
            cv = cv.split(" ")[0] if cv and "API calls" in cv else cv or "-"
            pub = _get_scraped_field(r, 'published_at') or "-"
            ep = _get_scraped_field(r, 'endpoint_type') or "unknown"
            ep = '🔓' if ep == 'free' else '🤝' if ep == 'partner' else ep
            depr = _get_scraped_field(r, 'deprecation_info') or ""
            depr_str = f'⚠️ {depr}' if depr else ""

            if r.status == 'success':
                status_icon = '✅'
                detail = '成功'
            elif r.status == 'timeout':
                status_icon = '⏰'
                detail = '超时'
            elif r.status == 'skipped':
                status_icon = '⏭️'
                detail = '跳过'
            else:
                status_icon = '❌'
                detail = r.error_message[:40] if r.error_message else r.status

            if depr_str:
                detail = f"{detail} ({depr_str})"

            model_id_str = f'{r.model_id} ⚠️' if depr else r.model_id
            md += f"| {r.rank} | {model_id_str} | {ep} | {cv} | {pub} | {tags_str} | {r.response_time:.2f}s | {status_icon} {detail} |\n"

        if image_results:
            md += """
---

## 🎨 文生图模型测试结果

| 热度排名 | 模型ID | 端点 | 调用量 | 发布时间 | 标签 | 响应时间 | 图片信息 | 状态/错误 |
|----------|--------|------|--------|----------|------|----------|----------|----------|
"""
            for r in image_results:
                tags_str = _format_tags(r.tags)
                cv = _get_scraped_field(r, 'call_volume') or ""
                cv = cv.split(" ")[0] if cv and "API calls" in cv else cv or "-"
                pub = _get_scraped_field(r, 'published_at') or "-"
                ep = _get_scraped_field(r, 'endpoint_type') or "unknown"
                ep = '🔓' if ep == 'free' else '🤝' if ep == 'partner' else ep
                depr = _get_scraped_field(r, 'deprecation_info') or ""
                depr_str = f'⚠️ {depr}' if depr else ""

                if r.status == 'success':
                    status_icon = '✅'
                    detail = '成功'
                    img_info = r.response_preview or '-'
                elif r.status == 'timeout':
                    status_icon = '⏰'
                    detail = '超时'
                    img_info = '-'
                elif r.status == 'skipped':
                    status_icon = '⏭️'
                    detail = '跳过'
                    img_info = '-'
                else:
                    status_icon = '❌'
                    detail = r.error_message[:40] if r.error_message else r.status
                    img_info = '-'

                if depr_str:
                    detail = f"{detail} ({depr_str})"

                model_id_str = f'{r.model_id} ⚠️' if depr else r.model_id
                md += f"| {r.rank} | {model_id_str} | {ep} | {cv} | {pub} | {tags_str} | {r.response_time:.2f}s | {img_info} | {status_icon} {detail} |\n"

        md += f"""
---

## 📋 标签说明
{TAG_LEGEND}

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return md

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

        md_file = f"{platform_dir}/{self.platform.upper()}_BATCH_TEST.md"
        json_file = f"{raw_dir}/{self.platform}_raw.json"

        md_content = self.md_formatter.format(report)
        self.md_formatter.save(md_content, md_file)

        json_content = self.json_formatter.format(report)
        self.json_formatter.save(json_content, json_file)

        return {'markdown': md_file, 'json': json_file}
