# API 模型测试工具 - 架构蓝图

**更新日期**: 2026-04-18

## 项目是什么
一个 **API 模型测试工具**，用于爬取、测试 NVIDIA 和智谱平台的免费模型，生成规范化的测试报告。

## 第一版要做什么
1. **A - 爬取模型列表**：按热度排序爬取各平台模型
2. **B - 批量测试**：测试模型可用性和响应速度
3. **C - 生成报告**：输出规范化的 Markdown/JSON 报告

## 明确不做什么
- 添加新平台（阿里云百炼、腾讯混元等以后再说）
- 数据库存储
- 用户登录系统
- 多用户支持

---

## 项目结构

```
api_key_test/
├── src/                         # 核心基础
│   ├── config_loader.py         # 环境配置加载
│   ├── models.py                # 统一数据结构
│   └── exceptions.py            # 自定义异常
│
├── platforms/                   # 各平台独立模块
│   ├── base/                    # 平台基类（定义接口）
│   │   ├── __init__.py
│   │   ├── base_scraper.py     # 爬虫基类
│   │   ├── base_tester.py       # 测试器基类
│   │   └── base_client.py      # API 客户端基类
│   │
│   ├── nvidia/
│   │   ├── __init__.py
│   │   ├── client.py           # NVIDIA API 客户端
│   │   ├── scraper.py          # NVIDIA 页面爬虫
│   │   └── tester.py           # NVIDIA 模型测试器
│   │
│   └── zhipu/
│       ├── __init__.py
│       ├── client.py            # 智谱 API 客户端
│       ├── scraper.py           # 智谱页面爬虫
│       └── tester.py            # 智谱模型测试器
│
├── report/                      # 报告生成（共用）
│   ├── __init__.py
│   ├── formatter.py             # 报告格式化器（共用）
│   └── generator.py             # 报告生成器（共用）
│
├── docs/                        # 文档输出（按平台分开）
│   ├── nvidia/                  # NVIDIA 测试报告
│   │   └── NVIDIA_BATCH_TEST_YYYYMMDD_HHMMSS.md
│   ├── zhipu/                  # 智谱测试报告
│   │   └── ZHIPU_BATCH_TEST_YYYYMMDD_HHMMSS.md
│   └── raw-data/               # JSON 原始数据
│       ├── nvidia/
│       │   └── nvidia_raw_YYYYMMDD_HHMMSS.json
│       └── zhipu/
│           └── zhipu_raw_YYYYMMDD_HHMMSS.json
│
└── scripts/                     # 入口脚本
    ├── test_nvidia.py           # 测试 NVIDIA 模型
    └── test_zhipu.py            # 测试智谱模型
```

---

## 文档命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| Markdown 报告 | `{平台}_{类型}_{日期时间}.md` | `NVIDIA_BATCH_TEST_20260418_120000.md` |
| JSON 原始数据 | `{平台}_raw_{日期时间}.json` | `nvidia_raw_20260418_120000.json` |

---

## 各模块接口定义

### 1. 平台基类 (platforms/base/)

```python
# platforms/base/base_scraper.py
from abc import ABC, abstractmethod
from typing import List
from ...src.models import ModelInfo

class BaseScraper(ABC):
    """爬虫基类"""

    @abstractmethod
    async def scrape(self, limit: int = 50) -> List[ModelInfo]:
        """
        爬取模型列表
        Args:
            limit: 爬取数量
        Returns:
            模型信息列表
        """
        pass

    def log_progress(self, current: int, total: int, message: str = ""):
        """输出进度日志，格式：[current/total] message"""
        print(f"\r[{current}/{total}] {message}", end="", flush=True)
```

```python
# platforms/base/base_tester.py
from abc import ABC, abstractmethod
from typing import List
from ...src.models import ModelInfo, TestResult

class BaseTester(ABC):
    """测试器基类"""

    @abstractmethod
    async def test(self, model: ModelInfo, timeout: int = 60) -> TestResult:
        """
        测试单个模型
        Args:
            model: 模型信息
            timeout: 超时时间(秒)
        Returns:
            测试结果
        """
        pass

    async def batch_test(self, models: List[ModelInfo],
                        concurrency: int = 3,
                        timeout: int = 60) -> List[TestResult]:
        """
        批量测试模型
        Args:
            models: 模型列表
            concurrency: 并发数
            timeout: 单个模型超时时间
        Returns:
            测试结果列表
        """
        pass

    def log_progress(self, current: int, total: int,
                    model_id: str, status: str, response_time: float = 0):
        """输出进度日志"""
        if status == "success":
            print(f"\r[{current}/{total}] ✅ {model_id} - {response_time:.2f}s")
        elif status == "failed":
            print(f"\r[{current}/{total}] ❌ {model_id} - {status}")
        elif status == "timeout":
            print(f"\r[{current}/{total}] ⏰ {model_id} - timeout")
```

```python
# platforms/base/base_client.py
from abc import ABC, abstractmethod
from typing import List, Iterator
from ...src.models import ChatMessage

class BaseClient(ABC):
    """API 客户端基类"""

    @abstractmethod
    def chat(self, model: str, messages: List[ChatMessage], **kwargs) -> str:
        """
        发送聊天请求
        Args:
            model: 模型ID
            messages: 消息列表
            **kwargs: 其他参数（max_tokens, temperature 等）
        Returns:
            模型回复文本
        """
        pass

    @abstractmethod
    def list_models(self) -> List[dict]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    def close(self):
        """关闭客户端"""
        pass
```

### 2. 报告生成器 (report/)

```python
# report/formatter.py
from abc import ABC, abstractmethod
from typing import List
from ..src.models import TestResult, TestReport

class BaseFormatter(ABC):
    """报告格式化器基类"""

    @abstractmethod
    def format(self, report: TestReport) -> str:
        """
        格式化报告
        Args:
            report: 测试报告数据
        Returns:
            格式化后的字符串
        """
        pass

    @abstractmethod
    def save(self, content: str, filepath: str):
        """保存报告到文件"""
        pass


class MarkdownFormatter(BaseFormatter):
    """Markdown 格式化器"""

    def format(self, report: TestReport) -> str:
        # 生成 Markdown 表格
        # 包含：排名、模型ID、标签、响应时间、状态
        pass

    def save(self, content: str, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


class JsonFormatter(BaseFormatter):
    """JSON 格式化器"""

    def format(self, report: TestReport) -> str:
        import json
        return json.dumps({
            'timestamp': report.timestamp,
            'platform': report.platform,
            'total': report.total,
            'success': report.success,
            'failed': report.failed,
            'timeout': report.timeout,
            'results': report.results
        }, ensure_ascii=False, indent=2)

    def save(self, content: str, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
```

```python
# report/generator.py
from datetime import datetime
from typing import List
from ..src.models import ModelInfo, TestResult, TestReport
from .formatter import MarkdownFormatter, JsonFormatter

class ReportGenerator:
    """报告生成器"""

    def __init__(self, platform: str):
        self.platform = platform
        self.markdown_formatter = MarkdownFormatter()
        self.json_formatter = JsonFormatter()

    def generate(self, results: List[TestResult],
                output_dir: str = "docs") -> dict:
        """
        生成报告
        Args:
            results: 测试结果列表
            output_dir: 输出目录
        Returns:
            包含文件路径的字典
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 构建报告数据
        report = TestReport(
            timestamp=datetime.now().isoformat(),
            platform=self.platform,
            total=len(results),
            success=sum(1 for r in results if r.status == 'success'),
            failed=sum(1 for r in results if r.status == 'failed'),
            timeout=sum(1 for r in results if r.status == 'timeout'),
            results=results
        )

        # 生成 Markdown
        md_content = self.markdown_formatter.format(report)
        md_file = f"{output_dir}/{self.platform}/#{self.platform.upper()}_BATCH_TEST_{timestamp}.md"
        self.markdown_formatter.save(md_content, md_file)

        # 生成 JSON
        json_content = self.json_formatter.format(report)
        json_file = f"{output_dir}/raw-data/{self.platform}/{self.platform}_raw_{timestamp}.json"
        self.json_formatter.save(json_content, json_file)

        return {'markdown': md_file, 'json': json_file}
```

### 3. 数据模型 (src/models.py)

```python
# src/models.py
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class ModelInfo:
    """模型信息"""
    id: str                          # 模型ID
    name: str                        # 显示名称
    vendor: str                      # 供应商
    rank: int = 0                    # 热度排名
    is_downloadable: bool = False    # 是否可下载
    is_free_endpoint: bool = True    # 是否有免费端点
    tags: List[str] = field(default_factory=list)  # 其他标签

@dataclass
class TestResult:
    """单个模型的测试结果"""
    model_id: str
    rank: int
    status: str                      # success / failed / timeout
    response_time: float = 0         # 响应时间(秒)
    error_message: str = ""          # 错误信息
    response_preview: str = ""       # 响应预览
    is_downloadable: bool = False
    is_free_endpoint: bool = True
    tags: List[str] = field(default_factory=list)

@dataclass
class TestReport:
    """测试报告"""
    timestamp: str
    platform: str
    total: int
    success: int
    failed: int
    timeout: int
    results: List[TestResult]

@dataclass
class ChatMessage:
    """聊天消息"""
    role: str                        # system / user / assistant
    content: str
```

---

## 开始写代码的顺序

1. **先实现 `src/models.py`** - 定义数据结构，最基础
2. **然后实现 `src/config_loader.py`** - 已有，复用
3. **实现 `platforms/base/`** - 定义平台接口
4. **实现 `platforms/nvidia/`** - NVIDIA 爬虫、测试器
5. **实现 `platforms/zhipu/`** - 智谱爬虫、测试器
6. **实现 `report/`** - 报告生成器
7. **最后写 `scripts/`** - 入口脚本

---

## 三个最需要注意的地方

| 风险 | 防范方式 |
|------|----------|
| **爬虫容易坏** - 页面结构改了就挂了 | 每个平台独立模块，改动不影响其他；爬虫有 fallback 方案 |
| **测试超时** - 网络不稳会导致大量超时 | 设置合理超时时间(默认60s)；捕获异常不中断批量测试 |
| **API Key 泄露** - 已通过 .env.local 解决 | 不在代码中硬编码；.gitignore 已配置 |