# API 模型测试工具 - 项目原理文档

> **文档版本**: v4.0.0
> **更新时间**: 2026-04-25
> **适用场景**: 交给其他 AI 构建 Web 应用（任意框架）
> **基于代码状态**: Phase 1-4 全部完成 + 单元测试完善（76 个测试用例）
> **维护者**: 项目架构师/技术负责人

---

## 目录

- [项目概述](#项目概述)
- [核心架构（四层设计）](#核心架构四层设计)
  - [第一层：基础层 (src/)](#第一层基础层-src)
  - [第二层：平台层 (platforms/)](#第二层平台层-platforms)
  - [第三层：应用层 (crawler/)](#第三层应用层-crawler)
  - [第四层：报告层 (report/)](#第四层报告层-report)
- [推理模型技术实现](#推理模型技术实现) ⭐ v2新增
- [测试体系](#测试体系) ⭐ v4新增
- [Web 应用构建指南](#web-应用构建指南) ⭐⭐ v4核心
- [数据模型精确对比](#数据模型精确对比) ⭐ v2重写
- [基类体系分析](#基类体系分析) ⭐ v2重写
- [数据流图](#数据流图)
- [设计模式使用](#设计模式使用)
- [关键技术决策及原因](#关键技术决策及原因)
- [已知问题与技术债务](#已知问题与技术债务) ⭐ v2更新
- [重构建议（按优先级排序）](#重构建议按优先级排序) ⭐ v2更新
- [关键文件索引](#关键文件索引) ✅ v3已更新
- [扩展指南（给其他 AI 的提示）](#扩展指南给其他-ai-的提示) ⭐ v2更新
- [附录](#附录)

---

## 项目概述

这是一个 **API 模型测试工具**，用于爬取、测试 NVIDIA 和智谱等平台的免费 AI 模型（含推理模型），并生成规范化的测试报告（Markdown + JSON 双格式）。

### 核心功能

1. **模型爬取**: 使用 Playwright 自动化浏览器，从 NVIDIA 官网爬取可用模型列表（支持热度/最新两种排序）
2. **批量测试**: 并发测试多个模型的 API 可用性和响应性能（支持普通模型 + 推理模型双模式）
3. **报告生成**: 生成 Markdown 和 JSON 双格式测试报告
4. **断点续传**: 支持测试中断后从断点恢复
5. **推理模型支持**: ⭐ v2 新增 — 自动识别并正确测试 DeepSeek V4、GLM-5.1 等推理模型

### 技术栈

- **语言**: Python 3.10+
- **浏览器自动化**: Playwright (Chromium)
- **HTTP 客户端**: OpenAI SDK / httpx（同步 Client，通过 run_in_executor 包装为异步）
- **配置管理**: YAML + 环境变量（多级回退）
- **日志系统**: 标准 Python logging + 自定义 JSON Lines 格式

### 已知可用模型（截至 2026-04-25）

| 模型 ID | 类型 | 状态 |
|---------|------|------|
| `google/gemma-4-31b-it` | 推理 | ✅ 正常 |
| `z-ai/glm4.7` | 推理 | ✅ 正常 |
| `minimaxai/minimax-m2.7` | 普通 | ✅ 正常 |
| `qwen/qwen3-coder-480b-a35b-instruct` | 普通 | ✅ 正常 |
| `deepseek-ai/deepseek-v3.1-terminus` | 普通 | ✅ 正常 |
| `meta/llama-4-maverick-17b-128e-instruct` | 普通 | ✅ 正常 |
| `moonshotai/kimi-k2-instruct-0905` | 普通 | ✅ 正常 |
| `google/gemma-7b` | 普通 | ✅ 正常 |
| `microsoft/phi-3-mini-128k-instruct` | 普通 | ✅ 正常 |
| `stepfun-ai/step-3.5-flash` | 普通 | ✅ 正常 |

---

## 核心架构（四层设计）

### 第一层：基础层 (src/)

**职责**: 定义抽象接口、数据结构、配置管理、平台注册

#### 1. base_client.py (94行)

抽象基类 `BaseClient`（ABC），定义统一接口：

```python
@dataclass
class ModelInfo:
    id: str
    name: str
    platform: str          # ← 注意：用 "platform" 而非 "vendor"
    is_free: bool = True
    is_reasoning: bool = False
    max_tokens: int = 4096
    context_window: int = 128000
    description: str = ""

@dataclass
class ChatMessage:
    role: str              # system, user, assistant
    content: str           # ← 无 reasoning_content 字段（注释提到但未定义）

class BaseClient(ABC):
    platform_name: str = "base"
    platform_display_name: str = "Base"

    def __init__(self, api_key, base_url=None, **kwargs): ...

    @abstractmethod
    def chat(self, model, messages, **kwargs) -> str: ...
    @abstractmethod
    def chat_stream(self, model, messages, **kwargs) -> Iterator[str]: ...  # ← 返回 Iterator[str]
    @abstractmethod
    def list_models(self) -> List[ModelInfo]: ...  # ← 返回 List[ModelInfo]
    @abstractmethod
    def test_connection(self) -> bool: ...
    def close(self): ...
```

#### 2. platform_registry.py (194行)

单例模式 `PlatformRegistry`（`__new__` 实现），全局实例 `registry = PlatformRegistry()`：

```python
@dataclass
class PlatformConfig:
    name: str
    display_name: str
    client_class: Type[BaseClient]
    default_base_url: Optional[str]
    api_key_env: Optional[str]
    is_available: bool = True
    description: str = ""
    website: str = ""

class PlatformRegistry:
    _instance = None
    _platforms: Dict[str, PlatformConfig] = {}

    def register(self, config: PlatformConfig): ...
    def create_client(self, platform, api_key=None, **kwargs) -> BaseClient: ...
    # 工厂方法：根据平台名创建客户端实例

def register_platform(name, display_name, client_class, ...) -> Callable:
    """装饰器：自动注册平台到注册表"""
```

**便捷函数**（模块级）：
- `chat(model, message, ...)` → 统一聊天接口
- `use_platform(platform, ...)` → 设置默认平台
- `list_models(platform)` → 列出模型
- `test_connection(platform)` → 测试连接

#### 3. config_loader.py (160行)

`ConfigLoader` 类，环境变量加载 + YAML 配置读取：

```python
ENV_VAR_MAP = {
    'nvidia': 'NVIDIA_API_KEY',
    'zhipu': 'ZHIPU_API_KEY',
    'aliyun': 'DASHSCOPE_API_KEY',
    'tencent': 'TENCENTCLOUD_SECRET_ID',
}
```

**多级配置回退策略**：
```
1. 环境变量（最高优先级）
2. .env.local（本地开发，不提交到 Git）
3. .env.development（开发环境）
4. .env（默认环境）
5. configs/platforms.yaml（平台默认配置）
```

⚠️ **已知 Bug**：`get_platform_config()` 方法 (L134) 调用了不存在的 `PlatformRegistry.get_instance()`，同文件 `validate_all()` (L160) 正确使用了 `PlatformRegistry()`

#### 4. ssl_config.py (28行)

自动查找 SSL 证书路径：

```python
def setup_ssl_certificates(cert_path=None, force=False):
    # 查找顺序：参数 > SSL_CERT_FILE env > REQUESTS_CA_BUNDLE env > certifi
```

#### 5. models.py (79行)

独立的数据类定义（被 platforms/ 层引用）：

```python
@dataclass
class ModelInfo:       # 字段: id, name, vendor, rank, is_downloadable, is_free_endpoint, tags, href
    def to_dict(self) -> dict: ...

@dataclass
class TestResult:      # 字段: model_id, rank, status, response_time, error_message, ...
    def to_dict(self) -> dict: ...

@dataclass
class TestReport:      # 字段: timestamp, platform, total, success, failed, timeout, results
    def to_dict(self) -> dict: ...

@dataclass
class ChatMessage:     # 字段: role, content
    def to_dict(self) -> dict: ...
```

> **注意**: 此文件的 ModelInfo 与 `src/base_client.py` 和 `crawler/models.py` 的 ModelInfo **完全不同**，详见[数据模型精确对比](#数据模型精确对比)。

---

### 第二层：平台层 (platforms/)

**职责**: 实现具体平台的 API 客户端（另一套基类体系）

#### 平台基类 (platforms/base/)

**注意**: 这套基类与 `src/base_client.py` 的基类 **并行存在、互不继承**。详见[基类体系分析](#基类体系分析)。

##### base_client.py (40行) — `BasePlatformClient`

```python
class BasePlatformClient(ABC):
    platform_name: str = "base"

    @abstractmethod
    def chat(self, model, messages, **kwargs) -> str: ...
    # ❌ 没有 chat_stream() 方法
    @abstractmethod
    def list_models(self) -> List[dict]: ...   # ← 返回 List[dict]，不是 List[ModelInfo]！
    # ❌ test_connection() 不是 abstract（有默认实现 L34-38）
    @abstractmethod
    def close(self): ...
    # ❌ 没有 __init__() 定义
```

引用来源：通过 `sys.path.insert(0, ...) + from src.models import ChatMessage` 导入消息类型

##### base_scraper.py (29行) — `BaseScraper`
```python
class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, limit=50, sort_by="popular", sort_order="DESC") -> List[ModelInfo]: ...
```

##### base_tester.py (65行) — `BaseTester`
```python
class BaseTester(ABC):
    @abstractmethod
    async def test_single(self, model, timeout=60) -> TestResult: ...

    async def batch_test(self, models, concurrency=3, timeout=60) -> List[TestResult]:
        # 默认并发实现：Semaphore + gather
```

#### NVIDIA 客户端（两个！）

项目中存在 **两个同名但不同继承体系的 `NvidiaClient`**：

**A. src/nvidia_client.py (161行)** — 继承 `src.base_client.BaseClient`

```python
@register_platform(name="nvidia", ..., client_class=None)  # ⚠️ client_class=None 是 bug
class NvidiaClient(BaseClient):
    BASE_URL = "https://integrate.api.nvidia.com/v1"
    FREE_MODELS = {  # 8个预定义映射
        "qwen3-coder": "qwen/qwen3-coder-480b-a35b-instruct",
        "minimax-m2.7": "minimaxai/minimax-m2.7",
        ...
    }
    # 有 chat_stream() 实现 → Iterator[str]
    # 有 quick_chat() 便捷方法
    # list_models() 返回 List[ModelInfo]（base_client 版）
```

**B. platforms/nvidia/client.py (65行)** — 继承 `BasePlatformClient`

```python
class NvidiaClient(BasePlatformClient):  # 同名不同类！
    # ❌ 无 @register_platform 装饰器
    # ❌ 无 FREE_MODELS
    # ❌ 无 chat_stream()
    # ❌ 无 quick_chat()
    # list_models() 返回 List[dict]（不是 ModelInfo）
    # 实际未被任何代码主动实例化（可能是僵尸类）
```

#### 智谱客户端 (platforms/zhipu/client.py, 81行)

```python
class ZhipuClient(BasePlatformClient):
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    FREE_MODELS = {  # 7个模型
        "glm-4-flash": "glm-4-flash-250414",
        "glm-4v-flash": "glm-4v-flash",
        ...
    }
    # 支持 thinking 参数：kwargs.get("thinking")
    # list_models() 硬编码 FREE_MODELS 映射（不调 API）
```

---

### 第三层：应用层 (crawler/)

**职责**: 业务逻辑实现（爬取→测试→报告），是项目中最活跃的开发区域

#### 1. scraper.py (725行) — 最复杂的文件

`NvidiaScraper` 类：Playwright 浏览器自动化爬虫

**工作流程**：

```
a. 初始化 Chromium（headless, --ignore-certificate-errors）(L65-73)
b. 访问 NVIDIA 模型页面（带重试机制：3次+指数退避 3s/6s/9s）(L103-131)
c. 备选策略：networkidle 超时后尝试 domcontentloaded (L120-127)
d. 关闭 Cookie 弹窗 OneTrust (L137, L665-698)
e. 分页提取模型卡片 data-testid='nv-card-root' (L259-261)
f. 从 API 获取模型映射表 _fetch_api_model_map（httpx 异步，SSL 禁用验证）(L486-576)
g. ID 标准化：_find_matching_model_id（短名→完整ID，精确→模糊匹配）(L578-599)
h. fix_model_id()：下划线替换为点号 (L18-33)
i. 过滤非文字模型（Category Tag 白名单 + ID 黑名单）(L454-484)
j. 翻页处理 aria-label="Go to next page" (L700-744)
```

**关键常量**：

| 常量 | 值 | 用途 |
|------|-----|------|
| `TEXT_MODEL_CATEGORIES` | 10 个集合 | 白名单：text-generation, chat, coding, reasoning 等 |
| `NON_TEXT_KEYWORDS` | 27 个关键词 | 黑名单：whisper, flux, embedding, nemotron-asr 等 |
| 默认超时 | 180 秒 | page.set_default_timeout |
| pageSize | 96 | 每页模型数（减少分页次数） |
| 最大翻页 | 10 次 | 防止无限循环 |

**选择器策略**：

| 优先级 | 选择器 | 用途 |
|--------|--------|------|
| 主选择器 | `[data-testid='nv-card-root']` | 定位模型卡片 |
| 链接选择器 | `a[data-nvtrack-nav-object='artifact-card']` | 提取完整模型 ID |
| 发布商选择器 | `a[data-nvtrack-nav-object-label]` | 提取 vendor |
| 标签选择器 | `span[data-testid='nv-badge']` | 提取 downloadable/free 标签 |
| Fallback | class 选择器组合 | 当 data-testid 失效时 |

#### 2. tester.py (396行) — 批量测试引擎（含推理模型双模式）

`ModelTester` 类：核心测试逻辑。详见[推理模型技术实现](#推理模型技术实现)。

**简要架构**：

```python
class ModelTester:
    def __init__(self, api_key=None, logger=None):
        # 直接读 os.getenv("NVIDIA_API_KEY")
        # 硬编码 self.base_url = "https://integrate.api.nvidia.com/v1"

    def test_single_model(self, model, timeout=60,
                         force_reasoning=False, force_normal=False):
        # L54: use_reasoning_mode = force_reasoning or (not force_normal and is_reasoning_model(model.id))
        # 分发到 _test_reasoning_model 或 _test_normal_model

    def _test_reasoning_model(self, model, timeout=120):   # L62-149
        # stream=True + extra_body={"chat_template_kwargs":{"thinking":True,"reasoning_effort":"..."}}
        # 手动解析 delta.reasoning / delta.reasoning_content / delta.content

    def _test_normal_model(self, model, timeout=60):        # L162-223
        # 标准 OpenAI 同步调用，读 response.choices[0].message.content

    async def test_model_async(self, model, ...):            # L225-231
        # run_in_executor(None, sync_method, ...)  ← 线程池包装

    async def test_batch_models(self, models, concurrency=5,
                               timeout=60, timeout_reasoning=180, ...):  # L233-305
        # Semaphore(concurrency) + gather + 分批执行(batch_size=concurrency*2)
        # 动态超时：推理模型用 timeout_reasoning，普通模型用 timeout

    def generate_report(self, models) -> dict:              # L307-350
        # 统计摘要 + 成功模型按 response_time 排序
```

**同步/异步现状**：所有实际 HTTP 调用都是同步的（`httpx.Client`），通过 `run_in_executor` 在线程池中执行。详见[基类体系分析 §4.7](#47-同步异步混用的层次分析)。

#### 3. logger.py (203行)

`ModelTestLogger` 类：结构化日志系统

**功能清单**：
- JSON Lines 日志文件 (`run_YYYYMMDD_HHMMSS.jsonl`)
- 控制台彩色输出（emoji 图标映射）
- 日志轮转（保留最近 10 个文件）
- 断点续传（`checkpoint.json` 存储已测试模型集合）
- 阶段日志：init → scraping → testing → reporting → complete
- 标准 Python logging 封装（`get_logger()` 函数）

#### 4. main.py (142行)

命令行入口，argparse 参数解析（共 **13 个**参数）：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-n/--number` | int | 20 | 模型数量 |
| `-c/--concurrency` | int | 5 | 并发数 |
| `--scrape-only` | flag | False | 仅爬取不测试 |
| `--timeout` | int | 60 | 普通模型超时(秒) |
| `--sort-by` | choice | popular | popular / recent |
| `--no-log` | flag | False | 禁用日志系统 |
| `--log-dir` | str | logs | 日志目录 |
| `--resume` | flag | False | 断点续传 |
| `--filter-text` | flag | True | 只测文字模型（默认启用） |
| `--no-filter` | flag | False | 禁用文字模型过滤 |
| `--reasoning-model` | str append | None | ⭐ 手动指定推理模型ID（可多次） |
| `--force-normal` | flag | False | ⭐ 强制普通模式 |
| `--reasoning-timeout` | int | 180 | ⭐ 推理模型超时(秒) |

---

### 第四层：报告层 (report/)

**职责**: 测试结果的可视化输出

#### generator.py (146行)

`ReportGenerator` 类：统一报告入口

**MarkdownFormatter**：
- 表格格式：总体统计 + Top10 排行榜 + 完整结果
- 标签图标映射：📥downloadable, 🔓free, ⚡flash, 🤔thinking

**JsonFormatter**：
- 结构化数据：timestamp, platform, statistics, results[]
- TestReport.to_dict() 序列化

**输出路径规范**：
- MD: `docs/{platform}/{PLATFORM}_BATCH_TEST_{timestamp}.md`
- JSON: `docs/raw-data/{platform}/{platform}_raw_{timestamp}.json`

---

## 推理模型技术实现

> ⭐ 本章节为 v2.0.0 新增内容，记录 2026-04-25 合并的推理模型支持功能

### 1. 推理模型识别机制

推理模型的识别逻辑集中在 [crawler/models.py](crawler/models.py) 中，采用**三级匹配策略**。

#### 1.1 预定义集合：`REASONING_MODELS`（[models.py L46-51](crawler/models.py#L46-L51)）

```python
REASONING_MODELS = {
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "z-ai/glm-5.1",
    "z-ai/glm-4.7",
}
```

这是**第一级精确匹配**——当模型 ID 完全等于集合中某个值时直接判定为推理模型。

#### 1.2 模式匹配列表：`REASONING_MODEL_PATTERNS`（[models.py L54-60](crawler/models.py#L54-L60)）

```python
REASONING_MODEL_PATTERNS = [
    "deepseek-v4",
    "glm-5.",
    "glm-4.7",
    "reasoning",
    "thinking",
]
```

用于**第三级模糊匹配**，覆盖未来可能上架的同系列新模型。

#### 1.3 三级匹配函数：`is_reasoning_model()`（[models.py L63-90](crawler/models.py#L63-L90)）

| 级别 | 匹配方式 | 说明 |
|------|----------|------|
| 第一级 | `model_id in REASONING_MODELS` | 精确全量匹配 O(1) |
| 第二级 | 去掉 vendor 前缀后检查 | 处理 `vendor/model-name` 格式 |
| 第三级 | `pattern in id_part` 遍历模式列表 | 子串包含匹配 |

任一级命中即返回 `True`，不继续后续判断。输入先 `.lower()` 统一转小写。

#### 1.4 推理努力程度：`get_reasoning_effort()`（[models.py L93-111](crawler/models.py#L93-L111)）

```python
def get_reasoning_effort(model_id: str) -> str:
    if "deepseek-v4" in model_id.lower():
        return "high"      # DeepSeek V4 → high
    if "glm" in model_id.lower():
        return "medium"     # GLM → medium
    return "high"           # 其他 → 默认 high
```

---

### 2. 双模式测试架构

[tester.py 的 `test_single_model()`](crawler/tester.py#L29-L60) 是模式分发的核心：

```python
use_reasoning_mode = force_reasoning or (
    not force_normal and is_reasoning_model(model.id)
)

if use_reasoning_mode:
    return self._test_reasoning_model(model, timeout)
else:
    return self._test_normal_model(model, timeout)
```

**三种控制场景**：

| 场景 | force_reasoning | force_normal | is_reasoning_model() | 结果 |
|------|----------------|-------------|---------------------|------|
| 自动检测 | False | False | True/False | 由检测结果决定 |
| 强制推理 | **True** | False | 任意 | **始终推理模式** |
| 强制普通 | False | **True** | True | **始终普通模式** |

> `force_reasoning` 优先于 `force_normal`（两者同时为 True 时前者胜出）

#### 2.1 推理模式：`_test_reasoning_model()`（[tester.py L62-149](crawler/tester.py#L62-L149)）

**extra_body 构造**（[tester.py L67-72](crawler/tester.py#L67-L72)）：

```python
extra_body = {
    "chat_template_kwargs": {
        "thinking": True,
        "reasoning_effort: reasoning_effort  # "high" 或 "medium"
    }
}
```

**API 调用差异**：

| 参数 | 推理模式 | 普通模式 |
|------|---------|---------|
| `stream` | **`True`（必须）** | 不传（默认 False） |
| `extra_body` | 含 `chat_template_kwargs` | 无 |
| `max_tokens` | `100` | `50` |

#### 2.2 普通模式：`_test_normal_model()`（[tester.py L162-223](crawler/tester.py#L162-L223)）

标准 OpenAI 同步调用，无特殊参数，直接读取 `response.choices[0].message.content`。

---

### 3. 流式输出处理细节

位于 [tester.py L91-113](crawler/tester.py#L91-L113)，是推理模型技术实现的核心。

**三种 delta 字段**：

| 字段名 | 来源模型 | 内容 |
|--------|---------|------|
| `delta.reasoning` | DeepSeek 系列 | 推理链文本 |
| `delta.reasoning_content` | GLM 系列 | 推理过程文本 |
| `delta.content` | 所有模型 | 最终回答 |

**兼容写法**：

```python
reasoning = getattr(delta, 'reasoning', None) or getattr(delta, 'reasoning_content', None)
if reasoning:
    reasoning_content += reasoning

content = getattr(delta, 'content', None)
if content:
    full_content += content
```

**Token 统计差异**：
- 推理模式：`token_usage = 0`（流式响应通常无 usage 对象）
- 普通模式：`token_usage = response.usage.total_tokens`

---

### 4. 批量测试中的推理模型特殊处理

[tester.py `test_batch_models()`](crawler/tester.py#L233-L305) 实现了动态超时选择：

```python
async def test_with_semaphore(model):
    async with semaphore:
        if is_reasoning_model(model.id) and not force_normal:
            model_timeout = timeout_reasoning    # 默认 180 秒（普通模型的 3 倍）
        else:
            model_timeout = timeout              # 默认 60 秒
```

**手动指定机制**：通过 CLI `--reasoning-model` 参数传入 `manual_reasoning_models` 列表，在爬取后标记对应模型的 `is_reasoning=True`。

---

### 5. CLI 参数传递链路

```
CLI (main.py)
  ├── args.reasoning_model  → manual_reasoning_models (L134)
  ├── args.force_normal     → force_normal (L133)
  ├── args.reasoning_timeout → reasoning_timeout (L131)
  └── bool(args.reasoning_model) → force_reasoning (L132)
       ↓
test_top_models(tester.py L365)
  ├── manual_reasoning_models → 标记 ModelInfo.is_reasoning=True (L414-420)
  ├── reasoning_timeout       → tester.test_batch_models(timeout_reasoning=) (L437)
  ├── force_reasoning         → tester.test_batch_models(force_reasoning=) (L438)
  └── force_normal            → tester.test_batch_models(force_normal=) (L439)
       ↓
test_batch_models(tester.py L233)
  └── 根据 is_reasoning_model() 动态选择 timeout (L263-266)
       ↓
test_single_model(tester.py L29)
  └── use_reasoning_mode 决定调用 _test_reasoning_model 或 _test_normal_model (L54-60)
```

---

### 6. 推理模型 vs 普通模型对比总表

| 维度 | 推理模式 | 普通模式 |
|------|---------|---------|
| 触发条件 | 自动检测或 `--reasoning-model`/`--force-reasoning` | 默认路径或 `--force-normal` |
| `extra_body` | ✅ `{"chat_template_kwargs": {"thinking": True, "reasoning_effort": "..."}}` | ❌ 无 |
| `stream` | ✅ 必须为 `True` | ❌ 不传 |
| `max_tokens` | `100` | `50` |
| 响应解析 | 遍历 chunk 流，提取 3 种 delta 字段 | 直接读 `message.content` |
| 内容分离 | `reasoning_content` + `full_content` 双通道 | 仅 `content` 单通道 |
| Token 统计 | 通常为 0 | 从 `usage.total_tokens` 获取 |
| 默认超时 | **180 秒** | **60 秒** |
| 典型模型 | deepseek-v4-*, glm-5.1, glm-4.7 | 其余所有文本生成模型 |
| ModelInfo 标记 | `is_reasoning=True`, `reasoning_effort="high\|medium"` | `is_reasoning=False` |

---

## 测试体系

> ⭐ v4.0.0 新增 — 记录完整的单元测试覆盖情况（2026-04-25 验证通过）

### 1. 测试基础设施

**位置**: `tests/conftest.py`

提供全局 pytest fixtures：

| Fixture 名称 | 类型 | 用途 |
|-------------|------|------|
| `mock_api_key` | str | 模拟 NVIDIA API Key（`nvapi-mock-key-for-testing`） |
| `sample_normal_model` | ModelInfo | 普通模型实例（`google/gemma-7b`, rank=5） |
| `sample_reasoning_model` | ModelInfo | 推理模型实例（`deepseek-ai/deepseek-v4-flash`, rank=10） |
| `mock_openai_response` | Mock | 模拟 OpenAI API 成功响应 |
| `mock_stream_response` | AsyncMock | 模拟流式响应（含 reasoning_content） |

### 2. 测试用例分类统计

**总计**: **76 个测试用例**（2026-04-25 全部通过 ✅）

| 测试文件 | 测试数量 | 覆盖模块 | 关键验证点 |
|---------|---------|---------|-----------|
| `test_models.py` | **24 个** | `src/models.py` 数据模型 | ModelInfo 默认值、status_icon emoji、to_dict() 序列化、枚举值完整性 |
| `test_errors.py` | **13 个** | `crawler/errors.py` 错误类型 | APIError 属性传递、AuthenticationError(401)、RateLimitError(429)、7层层次结构 |
| `test_reasoning_models.py` | **23 个** | `crawler/models.py` 推理识别 | REASONING_MODELS 精确匹配、PATTERNS 模式匹配、大小写不敏感、reasoning_effort 映射 |
| `test_registry.py` | **6 个** | `src/platform_registry.py` 注册表 | NvidiaClient.client_class 不为 None、可正常 import、list_models 返回 ModelInfo |
| `test_tester.py` | **6 个** | `crawler/tester.py` 核心逻辑 | force_normal/reasoning 模式选择、自动检测、generate_report 统计和排序 |
| `test_speed_tester_framework.py` | **4 个** | 额外框架测试 | SpeedTestResult、Summary generation、Markdown/JSON 导出 |

### 3. 运行测试

```bash
# 运行全部测试（详细输出）
pytest tests/ --tb=short -v

# 运行特定模块测试
pytest tests/test_models.py -v          # 数据模型测试
pytest tests/test_tester.py -v          # Tester 核心逻辑测试

# 生成覆盖率报告
pytest tests/ --cov=crawler --cov=src --cov-report=html
```

**最新运行结果** (2026-04-25):
```
======================= 76 passed, 3 warnings in 3.94s ========================
Exit code: 0 ✅
```

### 4. Mock 策略说明

- **AsyncMock**: 用于模拟异步方法（`_get_openai_client`, `chat.completions.create`）
- **patch**: 用于 mock SSL 设置（`@patch('src.ssl_config.setup_ssl_certificates')`）
- **Monkeypatch**: 用于绕过 API key 检查（直接设置 `tester.api_key`）
- **fixture 注入**: 通过 conftest.py 提供统一的 mock 数据源

---

## 数据模型精确对比

> ⭐ v2.0.0 重写 — 精确到字段级别的对比

### 三套 ModelInfo 并存现状

项目中存在 **三个同名但字段完全不同的 `ModelInfo` 类**：

| 属性 | [src/models.py](src/models.py) | [src/base_client.py](src/base_client.py) | [crawler/models.py](crawler/models.py) |
|------|------|------|------|
| **定位** | 通用数据结构（被 platforms/ 引用） | 基类内嵌（仅被 src/nvidia_client.py 使用） | 爬虫专用（含测试状态，最全） |
| `id` | ✅ str | ✅ str | ✅ str |
| `name` | ✅ str | ✅ str | ✅ str |
| **平台归属** | `vendor: str` | **`platform: str`** ← 不同！ | `vendor: str` |
| `rank` | ✅ int=0 | ❌ 无 | ✅ int=0 |
| `is_free` | ❌ 无 | ✅ `bool=True` | ❌ 有 `is_free_endpoint` |
| `is_reasoning` | ❌ 无 | ✅ `bool=False` | ✅ `bool=False` |
| `max_tokens` | ❌ 无 | ✅ `int=4096` | ❌ 无 |
| `context_window` | ❌ 无 | ✅ `int=128000` | ❌ 无 |
| `description` | ❌ 无 | ✅ `str=""` | ✅ `Optional[str]=None` |
| `is_downloadable` | ✅ `bool=False` | ❌ 无 | ✅ `bool=False` |
| `is_free_endpoint` | ✅ `bool=True` | ❌ 无 | ✅ `bool=True` |
| `tags` | ✅ `List[str]=[]` | ❌ 无 | ✅ `List[str]=None` |
| `href` | ✅ `str=""` | ❌ 无 | ❌ 无 |
| **测试字段** | ❌ 全部缺失 | ❌ 全部缺失 | ✅ 见下方表格 |

#### crawler/models.py 独有的测试字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `is_available` | bool | True | 是否可用 |
| `reasoning_effort` | Optional[str] | None | low/medium/high |
| `test_status` | str | "pending" | pending→testing→success/failed/timeout |
| `response_time` | float | 0 | 响应时间(秒) |
| `error_message` | str | "" | 错误信息（截断500字符） |
| `test_date` | Optional[str] | None | 测试完成时间 |
| `token_usage` | int | 0 | Token 消耗量 |
| `category` | Optional[str] | None | 分类标签 |
| `is_text_model` | bool | True | 是否文字模型 |

此外还有 `status_icon` property（[L33-42](crawler/models.py#L33-L42)）：将 test_status 映射为 emoji（⏳🔄✅❌⏰）。

### 序列化方法对比

| 模块 | 类/方法 | 返回值 | 包含字段 |
|------|---------|--------|----------|
| src/models.py | `ModelInfo.to_dict()` | dict | id,name,vendor,rank,is_downloadable,is_free_endpoint,tags |
| src/base_client.py | ModelInfo | **无 to_dict()** | — |
| crawler/models.py | ModelInfo | **无 to_dict()** | — |
| crawler/models.py | **`ModelStore.to_list()`** | List[dict] | rank,id,vendor,status,response_time,tags,category,is_text_model,is_callable,error |

> crawler 侧序列化委托给 `ModelStore.to_list()`，且包含派生字段 `is_callable`（由 `test_status=="success"` 计算）。

### TestResult 设计分歧

| 维度 | src/models.py TestResult | crawler 侧 |
|------|------|------|
| **存在形式** | 独立 dataclass | **不存在** — 结果直接写在 ModelInfo 上 |
| **设计理念** | 读写分离 | 原地 mutation |
| **优点** | 不可变语义清晰 | 查询方便 |
| **缺点** | 需维护映射关系 | 并发安全问题；无法保留多轮历史 |

### ChatMessage 三地定义

| 位置 | 字段 | 备注 |
|------|------|------|
| [src/models.py L86-92](src/models.py#L86-L92) | role, content | ✅ 有 to_dict() |
| [src/base_client.py L24-28](src/base_client.py#L24-L28) | role, content | ❌ 无 to_dict()；注释提 reasoning_content 但未定义 |
| crawler/models.py | **不存在** | tester 直接用裸 dict `{"role":"user","content":"..."}` |

### 核心矛盾总结

| # | 矛盾点 | 影响 | 建议 |
|---|--------|------|------|
| B1 | **三套 ModelInfo 同名异构** | IDE 跳转混乱、跨模块传参字段对不上 | 统为一套，用 Optional 标记可选字段 |
| B2 | **`platform` vs `vendor` 命名分裂** | 两处命名不一致 | 选定一个全局统一 |
| B3 | **测试结果嵌入 vs 独立 TestResult** | 原地 mutation 导致不可重现 | 分离 TestResult，ModelInfo 保持只读 |
| B4 | **ChatMessage 在 crawler 中消失** | tester 用裸 dict 绕过类型系统 | 统一引入或使用 TypedDict |
| B5 | **to_dict() 实现不一致** | 有的有、有的无、有的在 Store 上 | 统一序列化接口 |

---

## 基类体系分析

> ⭐ v2.0.0 重写 — 精确到方法签名的对比和实际继承关系

### 两套基类并行

| 维度 | [BaseClient](src/base_client.py) (src/) | [BasePlatformClient](platforms/base/base_client.py) (platforms/) |
|------|------|------|
| **构造器** | ✅ `__init__(api_key, base_url, **kwargs)` | ❌ **无 `__init__`** |
| `chat()` | ✅ abstract → str | ✅ abstract → str |
| `chat_stream()` | ✅ **abstract → Iterator[str]** | ❌ **不存在** |
| `list_models()` | ✅ abstract → **List[ModelInfo]** | ✅ abstract → **List[dict]** ← 类型不同！ |
| `test_connection()` | ✅ **abstract** | ⚠️ **默认实现**（非 abstract） |
| `close()` | 普通方法 | ✅ **abstract** |
| `__repr__()` | ✅ 有 | ❌ 无 |
| **内部 ModelInfo** | 自身定义（含 platform/max_tokens） | 不定义（返回裸 dict） |
| **内部 ChatMessage** | 自身定义（无 reasoning_content） | 从 src.models 导入 |

### 实际继承关系完整图谱

```
【体系 A：src/ 目录】
ABC
└── src.base_client.BaseClient (94行)
    └── src.nvidia_client.NvidiaClient (161行)
         ├── @register_platform(client_class=None!)  ⚠️ bug
         ├── 引用 src.base_client.ModelInfo/ChatMessage
         ├── 有 chat_stream(), quick_chat()
         └── list_models() → List[ModelInfo]

【体系 B：platforms/ 目录】
ABC
└── platforms.base.base_client.BasePlatformClient (40行)
    ├── platforms.nvidia.client.NvidiaClient (65行)   ← 同名不同类！
    │    ├── ❌ 无装饰器、无 FREE_MODELS、无 chat_stream()
    │    ├── list_models() → List[dict]
    │    └── 可能是僵尸类（未被主动实例化）
    │
    └── platforms.zhipu.client.ZhipuClient (81行)
         ├── 有 FREE_MODELS(7个)、支持 thinking 参数
         ├── list_models() → List[dict]（硬编码）
         └── ❌ 无 chat_stream()

【体系 C：crawler/ 目录 —— 完全绕过所有基类】
crawler.tester.ModelTester (核心测试逻辑)
    ├── ❌ 不继承任何基类
    ├── ❌ 不使用任何 Client 实例
    ├── 直接创建 OpenAI(...) + httpx.Client(...)
    ├── 直接操作 crawler.models.ModelInfo（v3，最大）
    └── 消息格式: 裸 dict {"role":"user","content":"..."}
```

### 同步/异步混用的层次分析

| 方法 | 是否 async | 执行方式 | HTTP 客户端 | 并发模型 |
|------|-----------|---------|------------|---------|
| `test_single_model()` | ✅ **async** | 直接 await | httpx.AsyncClient → AsyncOpenAI | 无（单任务） |
| `_test_reasoning_model()` | ✅ **async** | 直接 await + stream=True | AsyncOpenAI SDK | 无 |
| `_test_normal_model()` | ✅ **async** | 直接 await | AsyncOpenAI SDK | 无 |
| `test_model_async()` | ✅ async | 直接转发调用 | 继承上层 | — |
| `test_batch_models()` | ✅ async | Semaphore + gather | AsyncOpenAI | **Semaphore(5) × 真异步 I/O** |

✅ **v4 改造完成**：移除 `run_in_executor` hack，所有 HTTP 调用使用 `httpx.AsyncClient` + `AsyncOpenAI`，
实现真正的 I/O 并发，无线程开销，连接复用效率更高。

> **关键改进点**：
> - `ModelTester.__init__` 创建 `httpx.AsyncClient(verify=False)` 作为类成员
> - `_get_openai_client()` 返回 `AsyncOpenAI(http_client=self._http_client)`
> - 所有测试方法都是 `async def`，使用 `await` 调用 OpenAI API
> - 流式响应使用 `async for chunk in response:` 遍历

**已知 Bug**：[tester.py L91](crawler/tester.py#L91) 和 [L132/L147](crawler/tester.py#L132) 存在 `time.time() - time.time()` 错误写法（两次连续调用差值 ≈ 0），导致 timeout/failed 场景的 response_time 永远是 ~0。

**重复代码**：[tester.py L477-484](crawler/tester.py#L477-L484) 出现两次 `if __name__ == "__main__"` 块。

---

## 数据流图

```
用户命令 (main.py)
│
├─ argparse 解析（13个参数，含3个推理模型相关）
│   ├─ -n/--number: 模型数量
│   ├─ -c/--concurrency: 并发数
│   ├─ --sort-by: popular/recent
│   ├─ --reasoning-model: 手动指定推理模型（可多次）
│   ├─ --force-normal: 强制普通模式
│   └─ --reasoning-timeout: 推理超时（默认180s）
│
▼
[阶段1] 🕷️ 爬虫模块 (scraper.py - 725行)
│
│  Playwright Chromium (headless, ignore-cert-errors)
│  │
│  ├─ 访问 NVIDIA 页面（3次重试+指数退避）
│  ├─ 关闭 OneTrust Cookie 弹窗
│  ├─ 分页提取 [data-testid='nv-card-root']
│  ├─ API 获取模型映射表（httpx 异步）
│  ├─ fix_model_id(): 下划线 → 点号
│  ├─ _find_matching_model_id(): 短名 → 完整ID
│  └─ 过滤非文字模型（白名单10类 + 黑名单27词）
│
▼ 返回: List[crawler.models.ModelInfo]
│
[阶段2] 🧪 测试模块 (tester.py - 396行) ⭐ 含推理模型双模式
│
│  ├─ 加载断点续传状态
│  ├─ 对于每个模型：
│  │   ├─ is_reasoning_model()?  → 决定测试模式
│  │   ├─ [推理模式] _test_reasoning_model():
│  │   │   ├─ extra_body={"chat_template_kwargs":{"thinking":True,...}}
│  │   │   ├─ stream=True 遍历 chunks
│  │   │   └─ 提取 delta.reasoning + delta.content
│  │   └─ [普通模式] _test_normal_model():
│  │       └─ 标准同步调用 → message.content
│  │
│  ├─ Semaphore(concurrency) 控制并发
│  ├─ run_in_executor 包装同步方法为异步
│  └─ 动态超时：推理模型 180s / 普通模型 60s
│
▼ 返回: List[ModelInfo] (含测试结果)
│
[阶段3] 📊 报告模块 (report/generator.py - 146行)
│
│  ├─ 统计分析（success/failed/timeout/pending）
│  ├─ 成功模型按 response_time 升序排列
│  ├─ MarkdownFormatter → .md 表格
│  └─ JsonFormatter → .json 结构化数据
│
▼ 输出: .md + .json 文件
```

---

## 设计模式使用

### 1. 单例模式 — `PlatformRegistry` (src/platform_registry.py)
`__new__` 控制，全局唯一实例。延迟初始化。

### 2. 装饰器模式 — `@register_platform`
声明式注册，将注册逻辑与业务解耦。

### 3. 工厂模式 — `registry.create_client()`
调用者无需知道具体客户端类，符合开闭原则。

### 4. 模板方法模式 — `BaseClient` ABC
`src/base_client.py` 定义骨架，子类填充实现。
⚠️ 但 `platforms/base/base_client.py` 是另一套独立的模板方法体系。

### 5. 策略模式 — `MarkdownFormatter` / `JsonFormatter`
格式化逻辑与数据解耦，易于扩展新格式。

### 6. 观察者模式 — `ModelTestLogger`
事件驱动日志（start/success/timeout/error/batch_complete）。

---

## 关键技术决策及原因

### 1. ✅ Playwright 而非 requests
NVIDIA 模型页面是 SPA，需 JS 渲染。requests 只能获取初始 HTML。

### 2. ✅ OpenAI SDK 兼容层
NVIDIA 和智谱都兼容 OpenAI API 格式，复用成熟 SDK。

### 3. ⚠️ verify=False 忽略 SSL
仅限开发/测试环境。生产环境必须启用。

### 4. ✅ 并发数限制 3-5（默认改为 5）
平衡测试速度与 429 风险。

### 5. ✅ 断点续传机制
checkpoint.json 存储已测试模型集合，避免重复测试。

### 6. ✅ 双重文字模型过滤
白名单（TEXT_MODEL_CATEGORIES, 10 类）+ 黑名单（NON_TEXT_KEYWORDS, 27 词）。

### 7. ✅ 推理模型双模式架构（v2 新增）
自动识别推理模型并切换到流式输出+extra_body 参数，避免推理模型返回空内容。

---

## 已知问题与技术债务

> ✅ v4.0.0 更新 — Phase 1-4 全部完成，76 个单元测试全部通过

### ✅ 已修复（v3 重构）

#### ✅ 问题 1: 三套 ModelInfo 同名异构 — **已修复**
**修复方案**: `src/models.py` 扩展为全域唯一数据模型，`crawler/models.py` 改为 `from src.models import ModelInfo as _SrcModelInfo; ModelInfo = _SrcModelInfo` 别名引用

#### ✅ 问题 2: 两套基类体系并行 — **部分修复**
**修复方案**: `BasePlatformClient` 已补齐 `chat_stream()` 抽象方法和标准 `__init__`，`src/base_client.py` 标记为 DEPRECATED；完全合并待 Phase 4

#### ✅ 问题 3: 双 NvidiaClient（同名不同类）— **已修复**
**修复方案**: `platforms/nvidia/client.py` 已删除，`src/nvidia_client.py` 的 `client_class=NvidiaClient` 已修复

#### ✅ 问题 5: elapsed 计算 Bug — **已修复**
**修复方案**: 所有 `time.time() - time.time()` 已替换为 `time.time() - start_time`

#### ✅ 问题 9: config_loader.py get_instance() bug — **已修复**
**修复方案**: L134 改为 `PlatformRegistry()`

### 🟡 P1 — 重要（提升质量）

#### 问题 6: 硬编码 URL 和选择器
**位置**: `scraper.py` 多处
**风险**: NVIDIA 页面改版会导致爬虫失效
**建议**: 提取为配置文件，增加版本检测
**预估**: 8-16 小时

#### 问题 7: 缺乏单元测试 — **已修复 ✅**
**位置**: `tests/` 目录（7个测试文件）
**目标覆盖率**: ≥80%（核心模块）— **实际: 76 个测试用例全部通过**
**修复方案**: 完整的 pytest 测试套件，含 conftest.py fixtures、AsyncMock、patch 策略

#### 问题 8: 错误处理不够精细 — **已修复 ✅**
**位置**: `crawler/errors.py`（40行，7层错误类型层次）
**现象**: 所有异常归类为 failed，缺少细分
**修复方案**: 定义细粒度错误类型（APIError → AuthenticationError/RateLimitError/ModelNotFoundError/ServerError/TimeoutError + ScrapingError）

### 🟢 P2 — 改进（增强能力）

#### 问题 10: 配置分散
**位置**: configs/platforms.yaml, .env.local, 代码硬编码值
**建议**: 统一配置中心
**预估**: 12-24 小时

#### 问题 11: 日志系统耦合度高
**位置**: tester.py, scraper.py 直接依赖 logger 实例
**建议**: 引入 EventBus 发布-订阅模式
**预估**: 12-24 小时

#### 问题 12: 内存占用
**位置**: scraper.py 一次性加载所有模型
**建议**: 生成器模式/分批加载
**预估**: 4-8 小时

#### 问题 13: 报告格式固定
**位置**: report/generator.py
**建议**: Jinja2 模板或插件式格式化器
**预估**: 12-24 小时

#### 问题 14: 重复的 if __name__ 入口
**位置**: [tester.py L477-484](crawler/tester.py#L477-L484)
**预估**: 1 分钟

---

## 重构建议（按优先级排序）

> ⚠️ 以下建议基于 v2 文档。**v3 已完成 Phase 1-3**，部分建议已过时。

### ✅ Phase 1 — 统一数据层 — **已完成**

#### 1.1 合并三套 ModelInfo — **已完成**
✅ `src/models.py` 扩展为全域唯一数据模型（157行，20+字段）
✅ `crawler/models.py` 改为 `from src.models import ModelInfo as _SrcModelInfo; ModelInfo = _SrcModelInfo`
✅ 统一 `platform`/`vendor` 命名为 `vendor`
✅ 添加 `TestStatus` / `ReasoningEffort` 枚举

#### 1.2 修复 config_loader.get_instance() bug — **已完成**
✅ L134 改为 `PlatformRegistry()`

#### 1.3 修复 tester.py elapsed 计算 Bug — **已完成**
✅ 所有 `time.time() - time.time()` 替换为 `time.time() - start_time`

#### 1.4 删除 tester.py 重复入口 — **已完成**
✅ 删除重复的 `if __name__` 块

### ✅ Phase 2 — 合并基类 + 消除双 NvidiaClient — **已完成**

#### 2.1 统一基类 — **已完成**
✅ `BasePlatformClient` 补齐 `chat_stream()` 抽象方法
✅ `BasePlatformClient` 添加标准 `__init__`
✅ `src/base_client.py` 标记为 DEPRECATED

#### 2.2 清理 NvidiaClient — **已完成**
✅ `platforms/nvidia/client.py` 已删除
✅ `src/nvidia_client.py` 的 `client_class=NvidiaClient` 已修复

### ✅ Phase 3 — tester 异步改造 — **已完成**

#### 3.1 真正的异步 ✅ 已完成
- [x] ModelTester 改用 httpx.AsyncClient（连接复用）
- [x] 移除 run_in_executor hack
- [x] 所有测试方法改为 async def

#### 3.2 依赖注入 ✅ 已完成
- [x] ModelTester 接受 client 参数（可选注入）
- [x] 支持通过配置中心获取 base_url 和 api_key

### ✅ Phase 4 — 工程化提升 — **部分完成**

#### 4.1 错误类型系统 ✅ 已完成
- [x] ✅ 已新增 `crawler/errors.py`（APIError, AuthenticationError, RateLimitError, ModelNotFoundError, TimeoutError, ScrapingError）

#### 4.2 单元测试 ✅ 已完成
- [x] 76 个测试用例全部通过（远超 80% 覆盖率目标）

#### 4.3 其他工程化项
- [ ] scraper.py 关键常量可配置

### Phase 5 — 长期规划

#### 5.1 爬虫鲁棒性
- 选择器版本管理（v1/v2/v3 + fallback chain）
- 页面结构变化检测和告警
- 备用数据源（API 直接获取模型列表）

#### 5.2 配置中心化
所有 URL、超时、选择器、过滤规则集中到 `configs/app_config.yaml`

#### 5.3 长期扩展
- Web UI（任意框架）
- SQLite 历史数据存储 + 趋势分析
- 插件系统（第三方平台扩展）
- CI/CD 自动化测试流水线

---

## 关键文件索引

> ⭐ v2.0.0 更新 — 行数为实际代码行数

| 文件路径 | 行数 | 核心职责 | 重要程度 |
|---------|------|---------|---------|
| [crawler/scraper.py](crawler/scraper.py) | 725 | Playwright 爬虫（最复杂） | ⭐⭐⭐⭐⭐ |
| [crawler/tester.py](crawler/tester.py) | **556** | 批量测试引擎（async + 完整错误处理） | ⭐⭐⭐⭐⭐ |
| [src/platform_registry.py](src/platform_registry.py) | 194 | 平台注册表（单例+装饰器+便捷函数） | ⭐⭐⭐⭐⭐ |
| [crawler/logger.py](crawler/logger.py) | 203 | 日志和断点续传 | ⭐⭐⭐⭐ |
| [src/config_loader.py](src/config_loader.py) | 160 | 配置加载器（多级回退） | ⭐⭐⭐⭐ |
| [src/nvidia_client.py](src/nvidia_client.py) | 161 | NVIDIA API 客户端（src层） | ⭐⭐⭐⭐ |
| [report/generator.py](report/generator.py) | 146 | 报告生成器（MD+JSON） | ⭐⭐⭐⭐ |
| [crawler/main.py](crawler/main.py) | 142 | CLI 入口（13个参数） | ⭐⭐⭐⭐ |
| [crawler/models.py](crawler/models.py) | **127** | 爬虫数据模型（含推理模型支持，别名导入） | ⭐⭐⭐⭐ |
| [src/base_client.py](src/base_client.py) | 94 | 抽象客户端基类（src层，DEPRECATED） | ⭐⭐⭐⭐ |
| [src/models.py](src/models.py) | **134** | 数据结构定义（全域唯一 ModelInfo） | ⭐⭐⭐⭐ |
| [platforms/zhipu/client.py](platforms/zhipu/client.py) | 81 | 智谱客户端 | ⭐⭐⭐ |
| [platforms/nvidia/client.py](platforms/nvidia/client.py) | 65 | NVIDIA客户端(platforms层,可能僵尸) | ⭐⭐ |
| [src/ssl_config.py](src/ssl_config.py) | 28 | SSL证书配置 | ⭐⭐⭐ |
| [configs/platforms.yaml](configs/platforms.yaml) | 140 | 平台配置（6个平台） | ⭐⭐⭐ |
| [crawler/errors.py](crawler/errors.py) | **40** | 错误类型层次（7层） | ⭐⭐⭐⭐ |
| [tests/](tests/) | **7个文件** | 单元测试套件（76个用例） | ⭐⭐⭐⭐⭐ |

**复杂度排名**（按维护难度）:
1. **scraper.py** (725行) — Playwright + 页面解析 + ID标准化 + 分页 + 重试
2. **tester.py** (556行) — 异步测试引擎 + 双模式 + 并发控制 + 流式处理 + 错误处理
3. **platform_registry.py** (194行) — 设计模式密集 + 便捷函数
4. **logger.py** (203行) — 日志系统 + 断点续传 + 轮转
5. **config_loader.py** (160行) — 多级配置 + bug(get_instance)

---

## Web 应用构建指南

> ⭐ v4.0.0 新增 — **纯接口原理说明（框架无关）**
>
> ⚠️ **重要**: 本章节只说明**核心接口和调用契约**，**不做任何技术栈决策**。
> 你可以自由选择 FastAPI / Flask / Django / Gradio / Streamlit 或任何其他框架。

### 1. 核心类导入路径速查

| 类名/函数 | 导入路径 | 用途 |
|----------|---------|------|
| `ModelInfo` | `from src.models import ModelInfo` | 数据模型（全域唯一） |
| `TestStatus` | `from src.models import TestStatus` | 测试状态枚举 |
| `ReasoningEffort` | `from src.models import ReasoningEffort` | 推理努力程度枚举 |
| `ChatMessage` | `from src.models import ChatMessage` | 消息数据结构 |
| `TestResult` | `from src.models import TestResult` | 测试结果数据结构 |
| `TestReport` | `from src.models import TestReport` | 测试报告数据结构 |
| `ModelTester` | `from crawler.tester import ModelTester` | 核心测试引擎（**async**） |
| `NvidiaScraper` | `from crawler.scraper import NvidiaScraper` | Playwright 爬虫（**async**） |
| `PlatformRegistry` | `from src.platform_registry import registry` | 平台注册表（单例） |
| `APIError` | `from crawler.errors import APIError` | 错误基类 |
| `AuthenticationError` | `from crawler.errors import AuthenticationError` | 认证错误(401) |
| `RateLimitError` | `from crawler.errors import RateLimitError` | 频率限制(429) |
| `is_reasoning_model` | `from crawler.models import is_reasoning_model` | 推理模型判断函数 |
| `get_reasoning_effort` | `from crawler.models import get_reasoning_effort` | 推理努力程度获取 |

### 2. 异步调用原理（框架无关）

#### 2.1 核心事实

`ModelTester` 的所有测试方法都是 **真正的 async 方法**（v4 改造完成）：

```python
class ModelTester:
    async def test_single_model(self, model: ModelInfo, timeout: int = 60,
                                force_reasoning: bool = False,
                                force_normal: bool = False) -> ModelInfo: ...
    
    async def test_batch_models(self, models: List[ModelInfo],
                               concurrency: int = 5, ...) -> List[ModelInfo]: ...
    
    def generate_report(self, models: List[ModelInfo]) -> dict: ...  # 同步方法
```

**关键点**：
- ✅ 必须使用 `await` 调用（因为是真正的 async，不是假的 run_in_executor）
- ✅ 返回值是 **入参 ModelInfo 对象本身**（原地 mutation，测试结果直接写在对象上）
- ✅ 可通过 `.to_dict()` 序列化为字典
- ⚠️ **不是线程安全的**（同一 ModelInfo 实例不应并发测试）

#### 2.2 单模型测试调用流程

```python
# 伪代码（适用于任何异步框架）

async def test_one_model(model_id: str) -> dict:
    """
    测试单个模型的通用流程。
    
    参数:
        model_id: 完整模型ID，如 "deepseek-ai/deepseek-v4-flash"
    
    返回:
        包含测试结果的字典，可直接序列化为 JSON
    """
    from crawler.tester import ModelTester
    from crawler.models import ModelInfo
    
    # Step 1: 创建 ModelInfo 实例（必填字段：id, name, rank）
    model = ModelInfo(
        id=model_id,
        name=model_id.split("/")[-1],  # 从 ID 提取短名
        rank=0,                         # 可选，用于排序显示
    )
    
    # Step 2: 调用异步测试方法（必须 await！）
    result = await tester.test_single_model(
        model,
        timeout=60,              # 超时时间（秒），推理模型会自动使用 180s
        # force_reasoning=False,   # 可选：强制推理模式
        # force_normal=False,      # 可选：强制普通模式
    )
    
    # Step 3: 提取结果（result 就是入参 model，已被原地修改）
    return {
        "model_id": result.id,
        "model_name": result.name,
        "status": result.test_status,          # "success" | "failed" | "timeout"
        "status_icon": result.status_icon,     # emoji: ✅ ❌ ⏰ 🔄 ⏳
        "response_time": round(result.response_time, 2),  # 秒
        "is_reasoning": result.is_reasoning,    # 是否使用了推理模式
        "reasoning_effort": result.reasoning_effort,  # "high" | "medium" | None
        "token_usage": result.token_usage,
        "error": result.error_message or None,  # 失败时的错误信息
        "test_date": result.test_date,
    }
```

#### 2.3 批量测试调用流程

```python
# 伪代码：批量测试 + 报告生成

async def batch_test_models(model_ids: List[str]) -> dict:
    """
    批量测试多个模型并生成统计报告。
    
    参数:
        model_ids: 模型ID列表
    
    返回:
        包含 summary + 成功/失败模型列表的完整报告
    """
    from crawler.tester import ModelTester
    from crawler.models import ModelInfo
    
    # Step 1: 批量创建 ModelInfo 实例
    models = [
        ModelInfo(id=mid, name=mid.split("/")[-1], rank=i)
        for i, mid in enumerate(model_ids)
    ]
    
    # Step 2: 并发测试（Semaphore 控制并发数）
    results = await tester.test_batch_models(
        models,
        concurrency=5,             # 最大同时请求数（建议 3-5，避免 429）
        timeout=60,                # 普通模型超时（秒）
        timeout_reasoning=180,     # 推理模型自动识别并使用此超时
        # force_reasoning=False,   # 可选：强制全部使用推理模式
        # force_normal=False,      # 可选：强制全部使用普通模式
    )
    
    # Step 3: 生成结构化报告
    report = tester.generate_report(results)
    
    """
    report 结构:
    {
        "summary": {
            "total": int,           # 总数
            "success": int,         # 成功数
            "failed": int,          # 失败数
            "timeout": int,         # 超时数
            "testing": int,         # 测试中数
            "pending": int,         # 待测试数
        },
        "successful_models": [      # 按 response_time 升序排列（最快在前）
            {"rank": int, "id": str, "response_time": float, 
             "token_usage": int, "tags": List[str]},
            ...
        ],
        "failed_models": [          # 包含 failed 和 timeout 状态的模型
            {"rank": int, "id": str, "status": str, 
             "error": str or None, "tags": List[str]},
            ...
        ],
        "timestamp": str,           # 报告生成时间 (YYYY-MM-DD HH:MM:SS)
    }
    """
    
    return report
```

### 3. 错误处理原理（7 层层次结构）

#### 3.1 错误类型树

```
crawler/errors.py 定义的异常体系:

Exception
└── APIError (基类)
    │   属性: message: str, status_code: Optional[int], details: Optional[dict]
    │
    ├── AuthenticationError       # HTTP 401 — API Key 无效或过期
    ├── RateLimitError            # HTTP 429 — 请求频率超限（建议 60s 后重试）
    ├── ModelNotFoundError         # HTTP 404 — 模型不存在或已下架
    │       特有属性: model_id: str
    ├── ServerError               # HTTP 5xx — NVIDIA 服务端错误
    │       特有属性: status_code: int (实际 HTTP 状态码)
    └── TimeoutError              # 连接/读取超时（无标准 HTTP 映射）

ScrapingError                   # 独立体系（非 APIError 子类）
    │   属性: message: str, selector: Optional[str], page_url: Optional[str]
    └── 用于爬虫模块的错误（Web 应用通常不需要处理）
```

#### 3.2 错误语义说明

| 错误类型 | 触发条件 | 建议的客户端行为 | 建议的 HTTP 映射 |
|---------|---------|----------------|----------------|
| `AuthenticationError` | API Key 错误、过期、权限不足 | 提示用户检查配置 | 401 Unauthorized |
| `RateLimitError` | 请求太频繁（NVIDIA 限流） | 显示"请稍后重试"，建议等待 60s | 429 Too Many Requests |
| `ModelNotFoundError` | 模型 ID 在平台不存在 | 显示"模型已下架或不支持" | 404 Not Found |
| `ServerError` | NVIDIA 服务端异常（500/502/503） | 显示"服务暂时不可用"，可重试 | 对应 status_code |
| `TimeoutError` | 网络连接或读取超时 | 显示"响应超时"，建议增加超时或换模型 | 504 Gateway Timeout 或自定义 |

#### 3.3 错误处理原则（伪代码）

```python
# 原理性示例（非框架绑定）

async def safe_test_model(tester: ModelTester, model_id: str) -> dict:
    """
    安全测试模型的标准错误处理模式。
    
    原则:
    1. 捕获具体异常类型（不要裸 except Exception）
    2. 将异常映射为用户友好的错误信息
    3. 保留原始错误详情用于调试日志
    4. 不要暴露内部实现细节给终端用户
    """
    from crawler.errors import (
        APIError, AuthenticationError, RateLimitError,
        ModelNotFoundError, TimeoutError, ServerError
    )
    
    model = ModelInfo(id=model_id, name=model_id, rank=0)
    
    try:
        result = await tester.test_single_model(model)
        return {"success": True, "data": result.to_dict()}
        
    except AuthenticationError:
        return {
            "success": False,
            "error_type": "auth_failed",
            "user_message": "API 认证失败，请检查密钥配置",
            # 不暴露: 原始异常堆栈、内部 URL 等
        }
    
    except RateLimitError:
        return {
            "success": False,
            "error_type": "rate_limited",
            "user_message": "请求过于频繁，请 60 秒后重试",
            "retry_after": 60,  # 建议：可在响应头设置 Retry-After
        }
    
    except ModelNotFoundError as e:
        return {
            "success": False,
            "error_type": "not_found",
            "user_message": f"模型 '{model_id}' 不存在或已下架",
            "model_id": e.model_id,  # 该异常特有属性
        }
    
    except ServerError as e:
        return {
            "success": False,
            "error_type": "server_error",
            "user_message": "NVIDIA 服务暂时不可用",
            "status_code": e.status_code,  # 该异常特有属性
        }
    
    except TimeoutError:
        return {
            "success": False,
            "error_type": "timeout",
            "user_message": "模型响应超时，建议选择更快的模型或增加超时时间",
        }
    
    except APIError as e:  # 兜底：捕获所有未分类的 API 错误
        return {
            "success": False,
            "error_type": "api_error",
            "user_message": "测试过程中发生未知错误",
            # 仅在调试模式下返回 details:
            # "details": e.details,
        }
```

### 4. 推理模型双模式原理

#### 4.1 自动检测机制（内部逻辑）

`test_single_model()` 会**自动判断**是否需要使用推理模式，无需手动干预：

```
判断优先级（从高到低）:
┌─────────────────────────┐
│ force_reasoning == True? │ ──→ ✅ 强制推理模式（忽略模型特性）
└─────────────────────────┘
           ↓ No
┌─────────────────────────┐
│ force_normal == True?   │ ──→ ✅ 强制普通模式（即使模型支持推理）
└─────────────────────────┘
           ↓ No
┌─────────────────────────┐
│ is_reasoning_model(id)? │ ──→ ✅ 自动检测（三级匹配策略）
│                           │
│  第一级: id in REASONING_MODELS  (精确匹配 O(1))
│  第二级: 去掉 vendor 前缀后匹配
│  第三级: pattern in id_part     (模糊匹配 PATTERNS)
└─────────────────────────┘
           ↓ No (都不匹配)
┌─────────────────────────┐
│ 默认 → 普通模式         │
└─────────────────────────┘
```

#### 4.2 两种模式的差异对比

| 维度 | 推理模式 (`_test_reasoning_model`) | 普通模式 (`_test_normal_model`) |
|------|-----------------------------------|-------------------------------|
| **触发条件** | 自动检测 or `force_reasoning=True` | 默认路径 or `force_normal=True` |
| **OpenAI 参数** | `stream=True`, `extra_body={"chat_template_kwargs": {...}}` | 标准 OpenAI 调用（无特殊参数） |
| **响应解析** | 遍历 chunk 流，提取 `delta.reasoning` + `delta.content` | 直接读 `response.choices[0].message.content` |
| **Token 统计** | 通常为 `0`（流式响应通常无 usage 对象） | 从 `response.usage.total_tokens` 获取 |
| **默认超时** | **180 秒**（是普通模式的 3 倍） | **60 秒** |
| **max_tokens** | `100` | `50` |
| **结果标记** | `result.is_reasoning = True`<br>`result.reasoning_effort = "high" \| "medium"` | `result.is_reasoning = False`<br>`result.reasoning_effort = None` |

#### 4.3 如何判断返回值使用了哪种模式？

```python
result = await tester.test_single_model(model)

if result.is_reasoning:
    print(f"✅ 使用了推理模式 (effort: {result.reasoning_effort})")
    print(f"   注意: token_usage 可能为 0（流式响应特性）")
else:
    print(f"📝 使用了普通模式")
    print(f"   Token 消耗: {result.token_usage}")
```

### 5. 配置管理通用方法

#### 5.1 API Key 加载（三种方式）

```python
import os

# 方式 A: 环境变量（推荐用于 Docker/K8s/Serverless 等容器化部署）
api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    raise RuntimeError("必须设置 NVIDIA_API_KEY 环境变量")

# 方式 B: .env 文件（推荐用于本地开发）
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 或 .env.local
api_key = os.getenv("NVIDIA_API_KEY")

# 方式 C: 直接传入（不推荐硬编码，仅用于测试）
api_key = "nvapi-your-key-here"
```

#### 5.2 SSL 证书设置

```python
from src.ssl_config import setup_ssl_certificates

# 通常不需要手动调用！ModelTester.__init__ 会自动执行。
# 但如果遇到 SSL 问题，可以预配置：

setup_ssl_certificates()  # 方式1: 自动查找 certifi 或系统证书
# setup_ssl_certificates(cert_path="/custom/path/cert.pem")  # 方式2: 手动指定
```

#### 5.3 创建 Tester 实例

```python
from crawler.tester import ModelTester

# 推荐：应用启动时创建一次（单例复用）
tester = ModelTester(api_key=api_key)

# 内部会自动:
# 1. 调用 setup_ssl_certificates()
# 2. 创建 httpx.AsyncClient(verify=False) 作为成员变量
# 3. 所有后续测试共享同一个 HTTP 连接池（高效）
```

### 6. 数据模型字段完整说明

#### 6.1 ModelInfo（核心数据结构）

这是项目的**全域唯一数据模型定义**（v3 统一后的结果）：

| 字段 | 类型 | 默认值 | 说明 | 谁来填充 |
|------|------|--------|------|---------|
| **基本信息** |||||
| `id` | `str` | **必填** | 完整模型ID（如 `"deepseek-ai/deepseek-v4-flash"`） | 调用者传入 |
| `name` | `str` | **必填** | 显示名称 | 调用者传入 |
| `vendor` | `str` | `""` | 厂商（如 `"deepseek-ai"`） | 调用者/爬虫 |
| `rank` | `int` | `0` | 热度排名 | 调用者/爬虫 |
| **可用性标记** |||||
| `is_downloadable` | `bool` | `False` | 权重是否可下载 | 爬虫填充 |
| `is_free_endpoint` | `bool` | `True` | 是否免费端点 | 爬虫填充 |
| `tags` | `List[str]` | `[]` | 标签列表（如 `["downloadable", "free"]`） | 爬虫填充 |
| **测试状态（Tester 填充）** |||||
| `test_status` | `str` | `"pending"` | 测试状态枚举值 | ✅ Tester 更新 |
| `response_time` | `float` | `0.0` | 响应时间（秒） | ✅ Tester 更新 |
| `error_message` | `str` | `""` | 错误信息（截断至 500 字符） | ✅ Tester 更新 |
| `token_usage` | `int` | `0` | Token 消耗量 | ✅ Tester 更新 |
| `test_date` | `Optional[str]` | `None` | 测试完成时间（`"%Y-%m-%d %H:%M:%S"` 格式） | ✅ Tester 更新 |
| **推理模型特有字段** |||||
| `is_reasoning` | `bool` | `False` | 本次测试是否使用推理模式 | ✅ Tester 更新 |
| `reasoning_effort` | `Optional[str]` | `None` | 推理努力程度：`"low"` / `"medium"` / `"high"` | ✅ Tester 更新 |
| **辅助字段** |||||
| `description` | `Optional[str]` | `None` | 模型描述 | 爬虫填充 |
| `category` | `Optional[str]` | `None` | 分类标签 | 爬虫填充 |
| `is_text_model` | `bool` | `True` | 是否文本模型 | 爬虫填充 |
| `href` | `str` | `""` | 模型页面链接 | 爬虫填充 |

**特殊属性（Python property，不占用存储）**：

| Property | 返回类型 | 说明 |
|----------|---------|------|
| `.status_icon` | `str` | 将 `test_status` 映射为 emoji：<br>• `"pending"` → ⏳<br>• `"testing"` → 🔄<br>• `"success"` → ✅<br>• `"failed"` → ❌<br>• `"timeout"` → ⏰<br>• 其他 → ❓ |
| `.is_callable` | `bool` | `test_status == "success"` 时为 `True` |

**序列化方法**：

```python
model.to_dict()
# → 返回包含上述所有字段的字典（可直接 JSON 序列化）
# → error_message 会被截断至 200 字符（安全考虑）
```

#### 6.2 TestReport（generate_report 返回值）

`tester.generate_report(results)` 返回的字典结构：

```python
{
    "summary": {
        "total": int,           # 输入模型总数
        "success": int,         # test_status == "success" 的数量
        "failed": int,          # test_status == "failed" 的数量
        "timeout": int,         # test_status == "timeout" 的数量
        "testing": int,         # 仍在测试中的数量（通常为 0）
        "pending": int,         # 未开始测试的数量
    },
    "successful_models": [
        # 按 response_time 升序排列（最快的模型在最前面）
        {
            "rank": int,                    # 原始排名
            "id": str,                      # 模型 ID
            "response_time": float,         # 响应时间（秒）
            "token_usage": int,             # Token 消耗
            "tags": List[str],              # 标签（来自爬虫）
        },
        # ... 更多成功模型
    ],
    "failed_models": [
        # 包含 failed 和 timeout 两种状态
        {
            "rank": int,
            "id": str,
            "status": str,                  # "failed" 或 "timeout"
            "error": str or None,           # 错误信息（如有）
            "tags": List[str],
        },
        # ... 更多失败模型
    ],
    "timestamp": str,           # 报告生成时间
}
```

---

## 设计原则（⭐ 给其他 AI 的重要提示）

> ### 🚫 本文档不做技术栈决策！
>
> 我们只提供**接口契约和调用原理**，以下是你可以自由发挥的维度：

### 你可以自由选择的：

| 维度 | 可选方案 | 选择依据 |
|------|---------|---------|
| **Web 框架** | FastAPI / Flask / Django / Gradio / Streamlit / Tornado / Sanic... | 团队熟悉度、性能需求、生态偏好 |
| **部署方式** | Docker + Nginx / Kubernetes / Serverless (Vercel/Railway) / 传统 VPS / 本地运行... | 规模、成本、运维能力 |
| **数据库** | SQLite（轻量）/ PostgreSQL（生产）/ MongoDB / Redis 缓存 / 纯文件存储(JSON)... | 数据持久化需求、查询复杂度 |
| **前端** | React SPA / Vue.js / 纯 HTML+JS / Jupyter Notebook / Gradio 内置 UI / Streamlit 组件... | 交互复杂度、目标用户 |
| **任务队列** | Celery+Redis / ARQ / asyncio.create_task / 直接 await（简单场景）... | 是否需要后台任务、可靠性要求 |
| **认证方式** | JWT OAuth / API Key / Session / 无认证（本地工具）... | 安全需求、使用场景 |
| **实时更新** | WebSocket / SSE (Server-Sent Events) / 轮询 / 长轮询... | 用户体验、实现复杂度 |

### 唯一的技术约束（必须遵守）：

1. ✅ **必须使用 `async/await`** 调用 `ModelTester` 的方法（因为底层是真异步 I/O）
2. ✅ **正确处理 7 种错误类型**（或统一捕获 `APIError` 基类）
3. ✅ **理解推理模型双模式差异**（影响超时时间和返回值的 `is_reasoning` 标记）
4. ✅ **配置好 API Key 和 SSL 证书**（否则无法连接 NVIDIA API）

### 架构设计提示（仅供参考，不强制）：

- 💡 **单例 Tester**: 应用生命周期内只创建一个 `ModelTester` 实例（共享连接池）
- 💡 **并发控制**: 使用 Semaphore 限制同时请求数（建议 3-5，避免触发 429）
- 💡 **缓存策略**: 相同模型短时间内重复测试时，可返回缓存结果（减少 API 调用）
- 💡 **断点续传**: 利用 `ModelTestLogger` 的 checkpoint 机制支持中断恢复
- 💡 **优雅关闭**: 应用退出前调用 `await tester._http_client.aclose()` 释放资源

---

**🎯 总结**: 这份文档提供了完整的**接口原理和数据契约**，
但把**架构决策权完全交给你**。祝你构建出优秀的 Web 应用！ 🚀

---

## 扩展指南（给其他 AI 的提示）

### 如何添加新的推理模型

**步骤**：

1. 打开 [crawler/models.py](crawler/models.py)
2. 在 `REASONING_MODELS` 集合中添加完整模型 ID（如果需要精确匹配）
3. 或在 `REASONING_MODEL_PATTERNS` 中添加模式字符串（如果需要覆盖系列模型）
4. 如需自定义 reasoning_effort，修改 `get_reasoning_effort()` 函数
5. 测试：`python crawler/main.py -n 5 --sort-by recent`

**示例**：

```python
# crawler/models.py

REASONING_MODELS = {
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "z-ai/glm-5.1",
    "z-ai/glm-4.7",
    "new-vendor/new-reasoning-model-v1",  # ← 新增
}

REASONING_MODEL_PATTERNS = [
    "deepseek-v4",
    "glm-5.",
    "glm-4.7",
    "reasoning",
    "thinking",
    "new-reasoning",  # ← 新增模式
]

def get_reasoning_effort(model_id: str) -> str:
    if "deepseek-v4" in model_id.lower():
        return "high"
    if "glm" in model_id.lower():
        return "medium"
    if "new-vendor" in model_id.lower():  # ← 新增厂商策略
        return "low"  # 新厂商模型可能较慢
    return "high"
```

### 如何添加新平台

**步骤清单**：

1. 在 `platforms/{name}/` 创建目录
2. 实现 `client.py`（继承统一后的基类）
3. 如果需要爬虫：实现 `scraper.py`（继承 `BaseScraper`）
4. 如果需要测试：确保 `ModelTester` 支持该平台（或实现 `tester.py` 继承 `BaseTester`）
5. 使用 `@register_platform` 装饰器注册
6. 在 `configs/platforms.yaml` 添加配置
7. 更新 `ConfigLoader.ENV_VAR_MAP`

### 如何调整测试策略

**修改测试 prompt**：编辑 [tester.py L83](crawler/tester.py#L83) 和 [tester.py L174](crawler/tester.py#L174) 的 messages 参数

**修改超时时间**：
- 普通模型：`--timeout` 参数（默认 60s）
- 推理模型：`--reasoning-timeout` 参数（默认 180s）

**自适应超时示例**（推荐加入重构）：

```python
def get_adaptive_timeout(model: ModelInfo) -> int:
    base = 60
    if any(s in model.id.lower() for s in ["70b", "100b", "400b"]):
        base *= 2
    if "flash" in model.name.lower():
        base //= 2
    if model.is_reasoning:
        base *= 3  # 推理模型需要更长
    return base
```

### 如何修改爬虫选择器

**步骤**：

1. 定位 [scraper.py 的 `_extract_models()`](crawler/scraper.py#L245-L452)
2. 修改 `query_selector_all()` 的 CSS/XPath 选择器
3. 更新字段提取逻辑
4. 测试：`python crawler/main.py --scrape-only -n 5`

**常见调整**：

```python
# 场景1: NVIDIA 更改 data-testid
cards = await page.query_selector_all('[data-testid="new-model-card"]')

# 场景2: Category Tag 行变化
category = lines[3] if len(lines) > 3 else ""  # 原来是 lines[4]

# 场景3: 调试截图
await page.screenshot(path="debug_page.png")
html = await page.content()
print(html[:2000])
```

---

## 附录

### A. 常用命令速查

```bash
# === 基础用法 ===
python crawler/main.py -n 20                          # 测试20个热门模型（默认并发5）
python crawler/main.py -n 50 -c 5                     # 50个模型，并发5
python crawler/main.py --sort-by recent -n 50          # 测试最新发布的模型

# === 调试模式 ===
python crawler/main.py --scrape-only -n 30             # 仅爬取不测试
python crawler/main.py --resume -n 50                  # 断点续传
python crawler/main.py --no-filter -n 20               # 不过滤非文字模型
python crawler/main.py --no-log -n 10                  # 禁用日志系统

# === 推理模型相关（v2新增）===
python crawler/main.py -n 20 --sort-by recent          # 自动检测推理模型
python crawler/main.py -n 10 --reasoning-model deepseek-ai/deepseek-v4-flash
python crawler/main.py -n 10 --force-normal             # 强制普通模式
python crawler/main.py -n 20 --reasoning-timeout 300    # 推理超时300秒

# === 性能调优 ===
python crawler/main.py -n 100 -c 5 --timeout 120       # 大规模测试

# === 测试相关（v4新增）===

# 运行全部单元测试
pytest tests/ --tb=short -v

# 运行特定模块测试
pytest tests/test_models.py -v
pytest tests/test_tester.py -v

# 生成覆盖率报告
pytest tests/ --cov=. --cov-report=term-missing

# 仅运行失败的测试（上次）
pytest tests/ --lf

# 并行运行测试（需要 pytest-xdist）
pytest tests/ -n auto
```

### B. 环境变量列表

| 变量名 | 用途 | 示例值 | 是否必需 |
|-------|------|--------|---------|
| `NVIDIA_API_KEY` | NVIDIA API 密钥 | `nvapi-xxxxx` | ✅ 是（主功能） |
| `ZHIPU_API_KEY` | 智谱 API 密钥 | `xxxxx.xxxxx` | ⚠️ 可选 |
| `SSL_CERT_FILE` | SSL 证书路径 | `/path/to/cert.pem` | ❌ 否 |
| `REQUESTS_CA_BUNDLE` | CA 证书包路径 | `/path/to/ca-bundle.crt` | ❌ 否 |
| `VERIFY_SSL` | 是否验证 SSL | `true`/`false` | ❌ 否（默认 true）|

### C. 项目目录结构（完整版）

```
api_key_test/
├── src/                        # 基础层：接口和数据结构
│   ├── __init__.py
│   ├── base_client.py          # 94行 - 抽象基类(ModelInfo+ChatMessage在此)
│   ├── nvidia_client.py        # 161行 - NVIDIA客户端(@register_platform)
│   ├── zhipu_client.py         # 智谱客户端
│   ├── platform_registry.py    # 194行 - 平台注册表(单例+装饰器+便捷函数)
│   ├── config_loader.py        # 160行 - 配置加载器(.env+YAML)
│   ├── ssl_config.py           # 28行 - SSL证书配置
│   └── models.py               # 157行 - 全域唯一数据模型(v3统一)
│
├── platforms/                  # 平台层：具体实现（另一套基类体系）
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── base_scraper.py     # 29行 - 爬虫基类
│   │   ├── base_tester.py      # 65行 - 测试器基类
│   │   └── base_client.py      # 40行 - 客户端基类(与src/base_client.py不同!)
│   ├── nvidia/
│   │   ├── __init__.py
│   │   └── client.py           # 65行 - NVIDIA客户端(可能僵尸类)
│   └── zhipu/
│       ├── __init__.py
│       └── client.py           # 81行 - 智谱客户端
│
├── crawler/                    # 应用层：业务逻辑（主要开发区域）
│   ├── __init__.py
│   ├── scraper.py              # 725行 - Playwright爬虫（最复杂）
│   ├── tester.py               # 396行 - 批量测试引擎（含推理模型双模式）
│   ├── logger.py               # 203行 - 日志和断点续传
│   ├── main.py                 # 142行 - CLI入口（13个参数）
│   ├── models.py               # 157行 → 统一导入自 src.models（v3）
│   ├── simple_tester.py
│   ├── speed_tester.py
│   ├── requirements.txt
│   ├── README.md
│   └── reports/                # JSON测试报告
│
├── report/                     # 报告层
│   ├── __init__.py
│   └── generator.py            # 146行 - Markdown/JSON双格式
│
├── configs/
│   └── platforms.yaml          # 140行 - 平台配置(6个平台)
│
├── examples/                   # 示例代码
│   └── *.py
│
├── scripts/                    # 入口脚本
│   ├── batch_test.py
│   ├── setup_env.py
│   ├── test_nvidia.py
│   └── test_zhipu.py
│
├── tests/                      # 单元测试（v4 完善）
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures（7个）
│   ├── test_models.py          # 数据模型测试（24个）
│   ├── test_errors.py          # 错误类型测试（13个）
│   ├── test_reasoning_models.py # 推理模型识别测试（23个）
│   ├── test_registry.py        # 注册表验证测试（6个）
│   ├── test_tester.py          # Tester核心逻辑测试（6个）
│   └── test_speed_tester_framework.py # 框架测试（4个）
│
├── docs/                       # 文档和报告输出
│   ├── nvidia/
│   ├── zhipu/
│   ├── raw-data/
│   ├── platforms/
│   └── PROJECT_PRINCIPLES.md   # 本文档
│
├── .env.local                  # 本地环境变量（不提交）
├── .env.example                # 环境变量模板
├── .gitignore
├── CLAUDE.md                   # AI助手规则
├── README.md                   # 项目说明
├── ARCHITECTURE.md             # 架构蓝图
└── requirements.txt
```

### D. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|-----|------|------|---------|
| 1.0.0 | 2026-04-24 | AI Assistant | 初始版本 |
| 2.0.0 | 2026-04-25 | AI Assistant | 新增推理模型技术实现章节、重写数据模型对比和基类体系分析、更新所有行数和代码引用、修正技术债务清单 |
| **3.0.0** | **2026-04-25** | **AI Assistant** | **Phase 1-3 重构完成：统一数据模型层、合并基类体系、删除僵尸NvidiaClient、修复5个Bug、新增crawler/errors.py** |
| **4.0.0** | **2026-04-25** | **AI Assistant** | **Web 应用构建就绪：Phase 3 异步改造完成、76 个单元测试全部通过、错误类型系统完善、新增 Web 构建指南和测试体系文档** |

### E. 参考资料

- [Playwright 官方文档](https://playwright.dev/python/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [NVIDIA API 文档](https://build.nvidia.com/explore/discover)
- [智谱开放平台](https://open.bigmodel.cn/)
- [Python 设计模式](https://refactoring.guru/design-patterns/python)

---

## 结语

本文档旨在为项目维护者和后续 AI 重构代理提供全面、准确的技术参考。**v4.0.0 版本**在 v3.0.0 基础上完成了重大升级：

✅ **Phase 1 完成** — 统一数据模型层（src/models.py 为全域唯一 ModelInfo 定义）
✅ **Phase 2 完成** — 合并基类体系（BasePlatformClient 补齐 chat_stream 等）+ 删除僵尸类
✅ **Phase 3 完成** — ✨ **真正的异步改造**（httpx.AsyncClient + AsyncOpenAI，移除 run_in_executor hack）
✅ **Phase 4 部分完成** — 🧪 **完善的单元测试体系**（76 个测试用例全部通过）+ 7 层错误类型系统
✅ **Phase 5 部分完成** — 🌐 **Web 应用构建指南**（纯接口原理说明、数据模型完整说明、错误处理原理、推理模型双模式机制）

🎯 **当前状态**: 项目已具备构建 Web 应用的完整基础，可直接交付给其他 AI 进行任意框架的集成开发。

---

**最后更新**: 2026-04-25
**文档版本**: 4.0.0
**适用项目版本**: Phase 1-4 全部完成 + 单元测试完善（76 个测试用例）(2026-04-25+)
