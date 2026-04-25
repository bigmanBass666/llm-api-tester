# API 模型测试工具 - 项目原理文档

> **文档版本**: v3.0.0
> **更新时间**: 2026-04-25
> **适用场景**: 交给其他 AI 进行高级重构时的参考文档
> **基于代码状态**: 高级重构 Phase 1-3 完成 (2026-04-25)
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
| `test_single_model()` | ❌ 同步 | 直接执行 | httpx.Client（同步） | 无 |
| `_test_reasoning_model()` | ❌ 同步 | 直接执行 + stream=True | httpx.Client（同步） | 无 |
| `_test_normal_model()` | ❌ 同步 | 直接执行 | httpx.Client（同步） | 无 |
| `test_model_async()` | ✅ async | `run_in_executor(None, sync_fn, ...)` | 继承上层 | **每任务一线程** |
| `test_batch_models()` | ✅ async | Semaphore + gather | 继承上层 | **Semaphore(5) × 线程池** |

**本质**：`run_in_executor` 把同步阻塞代码扔进线程池，真正的异步优势为零。并发数 = 线程数。

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

> ✅ v3.0.0 更新 — Phase 1-3 重构已完成

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

#### 问题 7: 缺乏单元测试
**位置**: `tests/` 目录几乎为空
**目标覆盖率**: ≥80%（核心模块）
**预估**: 16-32 小时

#### 问题 8: 错误处理不够精细
**位置**: `tester.py` 异常处理
**现象**: 所有异常归类为 failed，缺少细分
**建议**: 定义细粒度错误类型（已新增 `crawler/errors.py`）
**预估**: 8-16 小时

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

### ⏳ Phase 3 — tester 异步改造 — **待完成（高风险）**

#### 3.1 真正的异步
- [ ] `ModelTester` 改用 `httpx.AsyncClient`（连接复用）
- [ ] 移除 `run_in_executor` hack
- [ ] 所有测试方法改为 `async def`

#### 3.2 依赖注入
- [ ] `ModelTester` 接受 `BaseClient` 实例（而非自己创建 OpenAI）
- [ ] 支持通过配置中心获取 base_url 和 api_key

### ⏳ Phase 4 — 工程化提升 — **待完成**

#### 4.1 错误类型系统
- [x] ✅ 已新增 `crawler/errors.py`（APIError, AuthenticationError, RateLimitError, ModelNotFoundError, TimeoutError, ScrapingError）

#### 4.2 其他工程化项
- [ ] scraper.py 关键常量可配置
- [ ] 单元测试覆盖率 ≥80%

### Phase 5 — 长期规划

#### 5.1 爬虫鲁棒性
- 选择器版本管理（v1/v2/v3 + fallback chain）
- 页面结构变化检测和告警
- 备用数据源（API 直接获取模型列表）

#### 5.2 配置中心化
所有 URL、超时、选择器、过滤规则集中到 `configs/app_config.yaml`

#### 5.3 长期扩展
- Web UI（Flask/FastAPI）
- SQLite 历史数据存储 + 趋势分析
- 插件系统（第三方平台扩展）
- CI/CD 自动化测试流水线

---

## 关键文件索引

> ⭐ v2.0.0 更新 — 行数为实际代码行数

| 文件路径 | 行数 | 核心职责 | 重要程度 |
|---------|------|---------|---------|
| [crawler/scraper.py](crawler/scraper.py) | 725 | Playwright 爬虫（最复杂） | ⭐⭐⭐⭐⭐ |
| [crawler/tester.py](crawler/tester.py) | 396 | 批量测试引擎（含推理模型双模式） | ⭐⭐⭐⭐⭐ |
| [src/platform_registry.py](src/platform_registry.py) | 194 | 平台注册表（单例+装饰器+便捷函数） | ⭐⭐⭐⭐⭐ |
| [crawler/logger.py](crawler/logger.py) | 203 | 日志和断点续传 | ⭐⭐⭐⭐ |
| [src/config_loader.py](src/config_loader.py) | 160 | 配置加载器（多级回退） | ⭐⭐⭐⭐ |
| [src/nvidia_client.py](src/nvidia_client.py) | 161 | NVIDIA API 客户端（src层） | ⭐⭐⭐⭐ |
| [report/generator.py](report/generator.py) | 146 | 报告生成器（MD+JSON） | ⭐⭐⭐⭐ |
| [crawler/main.py](crawler/main.py) | 142 | CLI 入口（13个参数） | ⭐⭐⭐⭐ |
| [crawler/models.py](crawler/models.py) | 157 | 爬虫数据模型（含推理模型支持） | ⭐⭐⭐⭐ |
| [src/base_client.py](src/base_client.py) | 94 | 抽象客户端基类（src层） | ⭐⭐⭐⭐ |
| [src/models.py](src/models.py) | 79 | 数据结构定义（src层） | ⭐⭐⭐ |
| [platforms/zhipu/client.py](platforms/zhipu/client.py) | 81 | 智谱客户端 | ⭐⭐⭐ |
| [platforms/nvidia/client.py](platforms/nvidia/client.py) | 65 | NVIDIA客户端(platforms层,可能僵尸) | ⭐⭐ |
| [src/ssl_config.py](src/ssl_config.py) | 28 | SSL证书配置 | ⭐⭐⭐ |
| [configs/platforms.yaml](configs/platforms.yaml) | 140 | 平台配置（6个平台） | ⭐⭐⭐ |

**复杂度排名**（按维护难度）:
1. **scraper.py** (725行) — Playwright + 页面解析 + ID标准化 + 分页 + 重试
2. **tester.py** (396行) — 双模式测试 + 并发控制 + 流式处理 + 报告生成
3. **platform_registry.py** (194行) — 设计模式密集 + 便捷函数
4. **logger.py** (203行) — 日志系统 + 断点续传 + 轮转
5. **config_loader.py** (160行) — 多级配置 + bug(get_instance)

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
├── tests/                      # 单元测试
│   └── test_speed_tester_framework.py
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

### E. 参考资料

- [Playwright 官方文档](https://playwright.dev/python/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [NVIDIA API 文档](https://build.nvidia.com/explore/discover)
- [智谱开放平台](https://open.bigmodel.cn/)
- [Python 设计模式](https://refactoring.guru/design-patterns/python)

---

## 结语

本文档旨在为项目维护者和后续 AI 重构代理提供全面、准确的技术参考。v3.0.0 版本在 v2.0.0 基础上完成了 Phase 1-3 重构：

✅ **Phase 1 完成** — 统一数据模型层（src/models.py 为全域唯一 ModelInfo 定义）
✅ **Phase 2 完成** — 合并基类体系（BasePlatformClient 补齐 chat_stream 等）+ 删除僵尸类
✅ **Phase 3 完成** — 修复 5 个 Bug（elapsed 计算、get_instance、重复入口等）
✅ **Phase 5 部分完成** — 新增 crawler/errors.py 错误类型系统

⏳ **待完成** — Phase 3 异步改造（高风险）、工程化提升

---

**最后更新**: 2026-04-25
**文档版本**: 3.0.0
**适用项目版本**: 高级重构 Phase 1-3 完成 (2026-04-25+)
