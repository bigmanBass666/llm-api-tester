"""
NVIDIA 模型测试日志系统
支持结构化 JSON Lines 日志、控制台输出、断点续传
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Set


class ModelTestLogger:
    """模型测试日志记录器"""

    def __init__(self, log_dir='logs', console_output=True, level='INFO'):
        """
        初始化日志器

        Args:
            log_dir: 日志目录
            console_output: 是否输出到控制台
            level: 日志级别
        """
        self.log_dir = Path(log_dir)
        self.console_output = console_output
        self.level = level

        # 创建 log 目录
        self.log_dir.mkdir(exist_ok=True)

        # 主日志文件（本次运行）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.log_dir / f'run_{timestamp}.jsonl'
        self.checkpoint_file = self.log_dir / 'checkpoint.json'

        # 轮转：保留最近 10 个 run_*.jsonl
        self._rotate_logs(keep=10)

        # 已测试模型集合（用于断点续传）
        self.tested_models: Set[str] = self._load_checkpoint()

        print(f"📝 日志系统初始化完成")
        print(f"   日志文件: {self.log_file}")
        print(f"   已测试模型: {len(self.tested_models)} 个")

    def log(self, level: str, event: str, model_id: str = None, rank: int = None, **extra) -> None:
        """
        记录结构化日志

        Args:
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
            event: 事件类型
            model_id: 模型ID
            rank: 热度排名
            **extra: 额外字段
        """
        entry = {
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'level': level,
            'event': event,
            'model_id': model_id,
            'rank': rank,
            **extra
        }

        # 写入文件（JSON Lines）
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"❌ 写入日志失败: {e}")

        # 控制台输出（简洁版）
        if self.console_output:
            self._print_console(entry)

    def _print_console(self, entry: Dict[str, Any]) -> None:
        """控制台彩色输出"""
        event = entry['event']
        level = entry['level']
        model = entry.get('model_id', '')

        symbols = {
            'start': '🚀',
            'success': '✅',
            'timeout': '⏰',
            'error': '❌',
            'scraping': '🔍',
            'batch_start': '📊',
            'phase': '📋',
            'checkpoint': '💾'
        }

        sym = symbols.get(event, '•')
        msg = f"{sym} {event}"
        if model:
            msg += f" {model}"
        if 'response_time' in entry:
            msg += f" - {entry['response_time']:.2f}s"
        if 'error' in entry:
            msg += f" - {entry['error']}"
        if 'total' in entry:
            msg += f" (总计: {entry['total']})"
        if 'progress' in entry:
            msg += f" ({entry['progress']})"

        print(msg)

    def _rotate_logs(self, keep: int = 10) -> None:
        """日志轮转：删除超出数量的旧日志"""
        try:
            logs = sorted(self.log_dir.glob('run_*.jsonl'), key=lambda x: x.stat().st_mtime)
            if len(logs) > keep:
                for old in logs[:-keep]:
                    old.unlink(missing_ok=True)
                print(f"🗑️  清理了 {len(logs) - keep} 个旧日志文件")
        except Exception as e:
            print(f"⚠️  日志轮转失败: {e}")

    def _load_checkpoint(self) -> Set[str]:
        """加载已测试模型集合"""
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text())
                tested = set(data.get('tested_models', []))
                print(f"💾 加载断点: {len(tested)} 个已测试模型")
                return tested
            except Exception as e:
                print(f"⚠️ 加载断点失败: {e}")
                return set()
        return set()

    def mark_tested(self, model_id: str) -> None:
        """标记模型为已测试"""
        self.tested_models.add(model_id)

    def save_checkpoint(self) -> None:
        """保存断点信息"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'tested_models': list(self.tested_models),
                'total_tested': len(self.tested_models)
            }
            self.checkpoint_file.write_text(json.dumps(data, indent=2))
            print(f"💾 断点已保存: {len(self.tested_models)} 个模型")
        except Exception as e:
            print(f"❌ 保存断点失败: {e}")

    def is_tested(self, model_id: str) -> bool:
        """检查模型是否已测试"""
        return model_id in self.tested_models

    def log_phase(self, name: str, **extra) -> None:
        """记录阶段开始"""
        self.log('INFO', 'phase', **{'name': name, **extra})

    def log_scraping(self, model_id: str, rank: int, tags: list = None, vendor: str = None) -> None:
        """记录爬取到模型"""
        self.log('INFO', 'scraping', model_id=model_id, rank=rank, tags=tags or [], vendor=vendor)

    def log_test_start(self, model_id: str, rank: int) -> None:
        """记录测试开始"""
        self.log('INFO', 'start', model_id=model_id, rank=rank)

    def log_test_success(self, model_id: str, response_time: float, token_usage: int = None) -> None:
        """记录测试成功"""
        extra = {'response_time': response_time}
        if token_usage:
            extra['token_usage'] = token_usage
        self.log('INFO', 'success', model_id=model_id, **extra)

    def log_test_timeout(self, model_id: str, timeout_seconds: int) -> None:
        """记录测试超时"""
        self.log('WARNING', 'timeout', model_id=model_id, timeout_seconds=timeout_seconds)

    def log_test_error(self, model_id: str, error_type: str, error_msg: str) -> None:
        """记录测试错误"""
        self.log('ERROR', 'error', model_id=model_id, error_type=error_type, error_msg=error_msg)

    def log_batch_complete(self, total: int, successful: int, failed: int, timeout: int) -> None:
        """记录批量测试完成"""
        self.log('INFO', 'batch_complete', total=total, successful=successful, failed=failed, timeout=timeout)

    def log_report_generated(self, output_path: str) -> None:
        """记录报告生成"""
        self.log('INFO', 'report_generated', output_path=output_path)


def create_logger(log_dir='logs', console_output=True, level='INFO') -> ModelTestLogger:
    """创建日志器实例"""
    return ModelTestLogger(log_dir=log_dir, console_output=console_output, level=level)