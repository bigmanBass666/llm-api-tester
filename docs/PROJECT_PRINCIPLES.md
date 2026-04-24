# API 模型测试工具 - 项目原理文档

> **文档生成时间**: 2026-04-24
> **适用场景**: 交给其他 AI 进行高级重构时的参考文档
> **维护者**: 项目架构师/技术负责人

---

## 目录

- [项目概述](#项目概述)
- [核心架构（三层设计）](#核心架构三层设计)
  - [第一层：基础层 (src/)](#第一层基础层-src)
  - [第二层：平台层 (platforms/)](#第二层平台层-platforms)
  - [第三层：应用层 (crawler/)](#第三层应用层-crawler)
  - [第四层：报告层 (report/)](#第四层报告层-report)
- [数据流图](#数据流图)
- [设计模式使用](#设计模式使用)
- [关键技术决策及原因](#关键技术决策及原因)
- [已知问题与技术债务](#已知问题与技术债务)
- [重构建议（按优先级排序）](#重构建议按优先级排序)
- [关键文件索引](#关键文件索引)
- [扩展指南（给其他 AI 的提示）](#扩展指南给其他-ai-的提示)

---

## 项目概述

这是一个 **API 模型测试工具**，用于爬取、测试 NVIDIA 和智谱等平台的免费 AI 模型，并生成规范化的测试报告（Markdown + JSON 双格式）。

### 核心功能

1. **模型爬取**: 使用 Playwright 自动化浏览器，从 NVIDIA 官网爬取可用模型列表
2. **批量测试**: 并发测试多个模型的 API 可用性和响应性能
3. **报告生成**: 生成 Markdown 和 JSON 双格式测试报告
4. **断点续传**: 支持测试中断后从断点恢复

### 技术栈

- **语言**: Python 3.10+
- **浏览器自动化**: Playwright (Chromium)
- **HTTP 客户端**: OpenAI SDK / httpx
- **配置管理**: YAML + 环境变量
- **日志系统**: 自定义 JSON Lines 格式

---

## 核心架构（三层设计）

### 第一层：基础层 (src/)

**职责**: 定义抽象接口、数据结构、配置管理

#### 1. base_client.py (L31-116)

抽象基类 `BaseClient`，定义统一接口：

```python
class BaseClient(ABC):
    @abstractmethod
    def chat(self, messages: List[ChatMessage], **kwargs) -> ChatMessage:
        """发送聊天请求"""
        pass

    @abstractmethod
    def chat_stream(self, messages: List[ChatMessage], **kwargs) -> Iterator[ChatMessage]:
        """流式聊天"""
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """获取模型列表"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接"""
        pass
```

**数据类定义**:

```python
@dataclass
class ModelInfo:
    model_id: str
    name: str
    vendor: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)

@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str
    reasoning_content: Optional[str] = None  # 推理模型专用
```

#### 2. platform_registry.py (L25-157)

单例模式 `PlatformRegistry`（`__new__` 实现）：

```python
class PlatformRegistry:
    _instance = None
    _platforms: Dict[str, Type[BaseClient]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, name: str, client_class: Type[BaseClient], api_key_env: str):
        """注册平台"""
        self._platforms[name] = {
            "class": client_class,
            "api_key_env": api_key_env
        }

    def create_client(self, name: str) -> BaseClient:
        """工厂方法：根据平台名创建客户端"""
        if name not in self._platforms:
            raise ValueError(f"Unknown platform: {name}")
        platform_info = self._platforms[name]
        api_key = os.environ.get(platform_info["api_key_env"])
        return platform_info["class"](api_key=api_key)
```

**装饰器自动注册**:

```python
def register_platform(name: str, api_key_env: str):
    """装饰器：自动注册平台到注册表"""
    def decorator(cls):
        PlatformRegistry().register(name, cls, api_key_env)
        return cls
    return decorator
```

#### 3. config_loader.py (L13-183)

`ConfigLoader` 类：环境变量加载、YAML 配置读取

**多级配置回退策略**:

```
1. 环境变量（最高优先级）
2. .env.local（本地开发，不提交到 Git）
3. .env.development（开发环境）
4. .env（默认环境）
5. configs/platforms.yaml（平台默认配置）
```

#### 4. ssl_config.py (L19-37)

自动查找 SSL 证书路径：

```python
def find_ssl_cert_path() -> Optional[str]:
    """
    SSL 证书查找顺序：
    1. 环境变量 SSL_CERT_FILE
    2. 环境变量 REQUESTS_CA_BUNDLE
    3. certifi 库提供的证书路径
    """
```

#### 5. models.py (在 src/ 和 crawler/ 各有一份)

数据类定义：`ModelInfo`, `TestResult`, `TestReport`, `ChatMessage`

**⚠️ 技术债务**: 两处定义略有不同，需要统一（见[已知问题](#已知问题与技术债务)）

---

### 第二层：平台层 (platforms/)

**职责**: 实现具体平台的 API 客户端

#### 1. NVIDIA 客户端 (src/nvidia_client.py)

继承 `BaseClient`，使用 OpenAI SDK 封装：

```python
@register_platform(name="nvidia", api_key_env="NVIDIA_API_KEY")
class NVIDIAClient(BaseClient):
    BASE_URL = "https://integrate.api.nvidia.com/v1"

    FREE_MODELS = {
        "gemma": "google/gemma-7b",
        "gemma-2-9b-it": "google/gemma-2-9b-it",
        "glm4.7": "z-ai/glm4.7"
    }

    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            base_url=self.BASE_URL,
            api_key=api_key,
            verify=False  # 忽略 SSL 验证
        )

    def chat(self, messages: List[ChatMessage], **kwargs) -> ChatMessage:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", "meta/llama-3.3-70b-instruct"),
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs
        )
        choice = response.choices[0]
        return ChatMessage(
            role="assistant",
            content=choice.message.content,
            reasoning_content=getattr(choice.message, "reasoning_content", None)
        )
```

**特殊处理**:
- **推理模型输出**: 在 `reasoning_content` 字段（L89-90）
- **FREE_MODELS 字典**: 短名称→完整ID映射
- **quick_chat() 便捷方法**: 封装常用场景

#### 2. 智谱客户端 (platforms/zhipu/client.py)

继承 `BasePlatformClient`：

```python
@register_platform(name="zhipu", api_key_env="ZHIPU_API_KEY")
class ZhipuClient(BasePlatformClient):
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    FREE_MODELS = [
        "glm-4-flash", "glm-4-air", "glm-4-long",
        "glm-4v-flash", "embedding-3", "cogview-4", "codegeex-4"
    ]
```

**特殊处理**:
- **thinking 参数支持**: 用于启用推理模型的思考过程输出
- **reasoning_content 兜底处理**: 兼容不同模型响应格式

#### 3. 平台基类 (platforms/base/)

**⚠️ 技术债务**: 与 `src/base_client.py` 存在重复（见[已知问题](#已知问题与技术债务)）

---

### 第三层：应用层 (crawler/)

**职责**: 业务逻辑实现（爬取→测试→报告）

#### 1. scraper.py (核心文件，862行)

`NvidiaScraper` 类：Playwright 浏览器自动化

**工作流程**:

```
a. 初始化 Chromium（headless模式，忽略SSL错误）(L66-76)
b. 访问 NVIDIA 模型页面（带重试机制，3次重试+指数退避）(L104-131)
c. 关闭 Cookie 弹窗（OneTrust）(L137, L665-698)
d. 分页提取模型卡片（data-testid='nv-card-root'）(L245-452)
e. 从 API 获取模型映射表（_fetch_api_model_map）(L486-576)
f. ID 标准化：网页短名 → API 完整ID（_find_matching_model_id）(L578-599)
g. 过滤非文字模型（Category Tag 白名单 + ID 关键词黑名单）(L454-484)
h. 翻页处理（aria-label="Go to next page"）(L700-744)
```

**关键技术点**:

| 技术点 | 实现方式 | 代码位置 |
|--------|----------|----------|
| 选择器策略 | 优先 data-testid，fallback 到 class 选择器 | L245-300 |
| 模型卡片结构解析 | innerText 第5行是 Category Tag | L320-340 |
| ID 标准化 | 网页短名 → API 完整ID 映射 | L578-599 |
| fix_model_id() | 下划线替换为点号 | L600-620 |
| TEXT_MODEL_CATEGORIES | text-generation, chat, coding 等 | L50-60 |
| NON_TEXT_KEYWORDS | whisper, flux, embedding 等 27 个关键词 | L62-88 |
| 重试机制 | 3次重试 + 指数退避 | L104-131 |

#### 2. tester.py (316行)

`ModelTester` 类：批量测试引擎

**单模型测试流程** (`test_single_model`, L29-103):

```python
async def test_single_model(self, model: ModelInfo) -> ModelInfo:
    # a. 检查断点续传
    if self.logger.is_tested(model.model_id):
        return model

    # b. 创建 OpenAI 客户端（verify=False 忽略SSL）
    # c. 发送简单请求："请回复'OK'"
    # d. 记录响应时间和 token 使用量
    # e. 分类状态：success / timeout / failed
```

**批量测试流程** (`test_batch_models`, L111-163):

- asyncio.Semaphore 控制并发数（默认3-5）
- run_in_executor 包装同步 HTTP 为异步
- 分批执行（batch_size = concurrency * 2）
- asyncio.gather 并发执行
- 异常隔离（return_exceptions=True）

#### 3. logger.py (246行)

`ModelTestLogger` 类：结构化日志系统

**功能**:
- JSON Lines 格式日志文件（run_YYYYMMDD_HHMMSS.jsonl）
- 控制台彩色输出（emoji 图标）
- 日志轮转（保留最近10个文件）
- 断点续传机制（checkpoint.json）
- 阶段日志：init → scraping → testing → reporting → complete

#### 4. main.py (152行)

命令行入口，argparse 参数解析

**支持的参数**:
- `-n/--number`: 模型数量（默认20）
- `-c/--concurrency`: 并发数（默认3）
- `--sort-by`: 排序方式（popular/recent）
- `--scrape-only`: 仅爬取不测试
- `--timeout`: 超时时间（默认60秒）
- `--resume`: 断点续传
- `--filter-text/--no-filter`: 文字模型过滤
- `--no-log`: 禁用日志系统

---

### 第四层：报告层 (report/)

**职责**: 测试结果的可视化输出

#### 1. generator.py (192行)

`ReportGenerator` 类：统一报告入口

**MarkdownFormatter**:
- 表格格式：总体统计 + Top10排行榜 + 完整结果
- 标签图标映射：📥downloadable, 🔓free, ⚡flash, 🤔thinking

**JsonFormatter**:
- 结构化数据：timestamp, platform, statistics, results[]
- TestResult.to_dict() 序列化

**输出路径规范**:
- MD: `docs/{platform}/{PLATFORM}_BATCH_TEST_{timestamp}.md`
- JSON: `docs/raw-data/{platform}/{platform}_raw_{timestamp}.json`

---

## 数据流图

```
用户命令 (main.py)
│
├─ argparse 参数解析
│   ├─ -n/--number: 模型数量
│   ├─ -c/--concurrency: 并发数
│   ├─ --sort-by: 排序方式 (popular/recent)
│   └─ 其他参数...
│
▼
[阶段1] 🕷️ 爬虫模块 (scraper.py)
│
│  ┌─────────────────────────────────────────────────────┐
│  │ 1. Playwright 启动 Chromium (headless)              │
│  │ 2. 访问 NVIDIA 页面（带重试机制）                   │
│  │ 3. 关闭 Cookie 弹窗 (OneTrust)                      │
│  │ 4. 分页提取模型卡片                                  │
│  │ 5. API 模型映射表获取                               │
│  │ 6. ID 标准化                                        │
│  │ 7. 过滤非文字模型                                   │
│  │ 8. 翻页处理                                         │
│  └─────────────────────────────────────────────────────┘
│
▼ 返回: List[ModelInfo]
│
[阶段2] 🧪 测试模块 (tester.py)
│
│  ┌─────────────────────────────────────────────────────┐
│  │ 1. 加载断点续传状态                                  │
│  │ 2. 并发控制 (Semaphore)                             │
│  │ 3. 逐个测试模型                                     │
│  │ 4. 分批执行                                         │
│  │ 5. 实时日志记录                                     │
│  └─────────────────────────────────────────────────────┘
│
▼ 返回: List[ModelInfo] (含测试结果)
│
[阶段3] 📊 报告模块 (report/generator.py)
│
│  ┌─────────────────────────────────────────────────────┐
│  │ 1. 统计分析                                         │
│  │ 2. 排序（成功模型按 response_time 升序）             │
│  │ 3. Markdown 格式化                                   │
│  │ 4. JSON 序列化                                      │
│  │ 5. 保存文件                                         │
│  └─────────────────────────────────────────────────────┘
│
▼ 输出: .md + .json 文件
```

---

## 设计模式使用

### 1. 单例模式 (Singleton Pattern)

**应用位置**: `PlatformRegistry` (src/platform_registry.py)

**实现方式**: 通过 `__new__` 方法控制实例化，全局唯一实例

**优点**:
- 全局唯一的注册表，避免重复注册
- 所有模块共享同一份平台配置
- 延迟初始化，节省资源

---

### 2. 装饰器模式 (Decorator Pattern)

**应用位置**: `@register_platform` 装饰器

**优点**:
- 声明式注册，代码简洁
- 将注册逻辑与业务逻辑解耦
- 符合 Python 风格

---

### 3. 工厂模式 (Factory Pattern)

**应用位置**: `registry.create_client()` 方法

**优点**:
- 调用者无需知道具体的客户端类
- 新增平台只需添加装饰器，无需修改工厂代码
- 符合开闭原则

---

### 4. 模板方法模式 (Template Method Pattern)

**应用位置**: `BaseClient` 抽象基类

**类层次结构**:
```
BaseClient (ABC)
├── NVIDIAClient (NVIDIA 平台实现)
└── ZhipuClient (智谱平台实现)
```

---

### 5. 策略模式 (Strategy Pattern)

**应用位置**: `MarkdownFormatter` / `JsonFormatter`

**优点**:
- 格式化逻辑与报告数据解耦
- 易于扩展新格式（HTML、PDF、CSV）
- 运行时可切换策略

---

### 6. 观察者模式 (Observer Pattern)

**应用位置**: `ModelTestLogger` 事件驱动日志

**优点**:
- 业务逻辑与日志解耦
- 可添加多个观察者（控制台、文件、数据库）
- 符合单一职责原则

---

## 关键技术决策及原因

### 1. ✅ 使用 Playwright 而非 requests

**决策**: 使用 Playwright 进行浏览器自动化爬取

**原因**:
- NVIDIA 模型页面是 **SPA（Single Page Application）**
- 内容通过 JavaScript 动态渲染
- requests 只能获取初始 HTML，无法获取渲染后的内容

**权衡**:

| 方面 | Playwright | requests |
|------|------------|----------|
| 能力 | ✅ 可渲染 JS | ❌ 仅静态 HTML |
| 性能 | ⚠️ 较慢 | ✅ 快速 |
| 资源占用 | ⚠️ 高 (~200MB) | ✅ 低 |

**结论**: 功能需求优先于性能

---

### 2. ✅ OpenAI SDK 兼容层

**决策**: 使用 OpenAI Python SDK 调用 NVIDIA 和智谱 API

**好处**:
- NVIDIA 和智谱都兼容 OpenAI API 格式
- 复用成熟的 SDK，减少 HTTP 手动处理
- 自动处理重试、超时、错误码等

---

### 3. ⚠️ verify=False 忽略 SSL

**决策**: 在 HTTP 客户端中禁用 SSL 证书验证

**风险**:
- 🔴 中间人攻击（MITM）- API Key 泄露
- 🟡 敏感数据泄露

**缓解措施**:
- ✅ 仅限开发/测试环境
- ✅ 生产环境必须启用验证
- ✅ 使用 `.env.local` 不提交敏感配置

---

### 4. ✅ 并发数限制为 3-5

**决策**: 默认并发数为 3，最大建议不超过 5

**权衡分析**:

| 并发数 | 测试速度 | 429 风险 | 推荐度 |
|-------|---------|---------|-------|
| 1 | 极慢 | 无 | ⭐⭐ |
| 3 | 适中 | 低 | ⭐⭐⭐⭐⭐ |
| 5 | 较快 | 中 | ⭐⭐⭐⭐ |
| 10 | 快 | 高 | ⭐⭐ |

**结论**: **3-5 是最佳平衡点**

---

### 5. ✅ 断点续传机制

**决策**: 实现 checkpoint-based 断点续传

**原因**:
- 批量测试耗时很长（50个模型需 30-60 分钟）
- 网络不稳定可能导致中断
- 避免重复测试已完成的模型

**实现**: checkpoint.json 存储已测试模型集合

---

### 6. ✅ 文字模型过滤

**决策**: 双重策略过滤非文字模型

**原因**:
- 非文字模型无法用 "回复OK" 测试
- 语音/图像/嵌入模型会产生无意义错误

**策略**:
- 白名单: TEXT_MODEL_CATEGORIES (text-generation, chat, coding...)
- 黑名单: NON_TEXT_KEYWORDS (whisper, flux, embedding... 27个)

---

## 已知问题与技术债务

### 🔴 高优先级问题（影响可维护性）

#### 问题 1: 重复的数据模型定义

**位置**: `src/models.py` vs `crawler/models.py`

**问题描述**: ModelInfo 类在两个文件中各定义了一遍，字段略有不同

**影响**:
- 数据转换时可能丢失字段
- IDE 类型推断混乱
- 维护成本翻倍

**建议修复方案**: 统一为一个数据模型模块（推荐使用 Pydantic）

**优先级**: P0（紧急） | **预估工作量**: 2-4 小时

---

#### 问题 2: BaseClient 继承混乱

**位置**: `src/base_client.py` vs `platforms/base/base_client.py`

**问题描述**: 存在两个不同的基类，命名相同但实现不同

**影响**:
- 多态代码无法正常工作
- 类型检查困难
- 新开发者困惑

**建议修复方案**: 统一基类，或明确区分用途

**优先级**: P0（紧急） | **预估工作量**: 4-8 小时

---

#### 问题 3: 同步/异步混用

**位置**: `tester.py` L107-109

**问题描述**: test_single_model() 是同步方法，用 run_in_executor 包装成异步

**影响**:
- run_in_executor 创建额外线程开销
- 嵌套 asyncio.run() 可能导致事件循环冲突
- 错误堆栈难以追踪

**建议修复方案**: 全面改用 async httpx

**优先级**: P0（紧急） | **预估工作量**: 6-12 小时

---

#### 问题 4: 硬编码的 URL 和选择器

**位置**: `scraper.py` 多处

**问题描述**: URL 和 CSS 选择器硬编码在代码中

**风险**: NVIDIA 页面改版会导致爬虫失效

**建议修复方案**: 提取为配置文件，增加版本检测和 fallback

**优先级**: P1（重要） | **预估工作量**: 8-16 小时

---

### 🟡 中优先级问题（提升质量）

#### 问题 5: 缺乏单元测试

**位置**: `tests/` 目录几乎为空

**目标覆盖率**: ≥80%（核心模块）

**预估用例数**: ~105 个

**优先级**: P1（重要） | **预估工作量**: 16-32 小时

---

#### 问题 6: 错误处理不够精细

**位置**: `tester.py` L90-103

**问题描述**: 所有异常都归类为 failed，缺少细分

**建议**: 定义细粒度错误类型（AuthError, RateLimitError, ModelNotFoundError...）

**优先级**: P1（重要） | **预估工作量**: 8-16 小时

---

#### 问题 7: 日志系统耦合度高

**位置**: `tester.py`, `scraper.py`

**建议**: 引入 EventBus 或信号槽机制（发布-订阅模式）

**优先级**: P1（重要） | **预估工作量**: 12-24 小时

---

#### 问题 8: 配置分散

**位置**: `configs/platforms.yaml`, `.env.local`, 代码中的硬编码值

**建议**: 统一配置中心（configs/app_config.yaml）

**优先级**: P1（重要） | **预估工作量**: 16-24 小时

---

### 🟢 低优先级问题（增强能力）

#### 问题 9: 内存占用

**位置**: `scraper.py` 一次性加载所有模型到内存

**建议**: 流式处理或分批加载（生成器模式）

**优先级**: P2（改进） | **预估工作量**: 4-8 小时

---

#### 问题 10: 报告格式固定

**位置**: `report/generator.py`

**建议**: 支持 Jinja2 模板或插件式格式化器

**优先级**: P2（改进） | **预估工作量**: 12-24 小时

---

#### 问题 11: 缺少数据持久化

**位置**: 测试结果仅保存在 JSON 文件

**建议**: 可选的数据库存储（SQLite）用于历史查询和趋势分析

**优先级**: P2（改进） | **预估工作量**: 16-24 小时

---

#### 问题 12: 平台扩展性

**当前状态**: 仅完整实现 NVIDIA，智谱部分实现

**建议**: 提供脚手架工具或更清晰的扩展指南

**优先级**: P3（锦上添花） | **预估工作量**: 24-40 小时

---

## 重构建议（按优先级排序）

### P0 - 紧急（影响可维护性）

#### 1. 统一数据模型

**目标**: 合并 src/models.py 和 crawler/models.py

**实施方案**:
- 定义严格的字段 schema（使用 Pydantic）
- 所有模块引用同一处定义
- 添加序列化/反序列化验证

**预期收益**:
- ✅ 消除数据不一致 bug
- ✅ IDE 支持更好
- ✅ 维护成本降低 50%

---

#### 2. 统一基类体系

**目标**: 明确 src/base_client.py 为唯一的客户端基类

**实施方案**:
- platforms/base/ 的基类应继承或别名 src/base_client.py
- 或重构为：src/ 只定义数据类，platforms/base/ 定义行为基类

**预期收益**:
- ✅ 清晰的继承层次
- ✅ 多态代码正常工作
- ✅ 降低新人学习成本

---

#### 3. 异步改造

**目标**: 将 tester.py 改为纯异步（async httpx）

**实施方案**:
- 移除 run_in_executor hack
- 统一使用 asyncio 和 httpx 异步客户端
- 所有 I/O 操作改为 await

**预期收益**:
- ✅ 性能提升 20-30%
- ✅ 代码更简洁
- ✅ 错误处理更清晰

---

### P1 - 重要（提升质量）

#### 4. 配置中心化

**目标**: 将所有配置集中到 configs/app_config.yaml

**包括**: URL、超时时间、并发数、选择器、过滤规则等

**支持**: 环境变量覆盖

---

#### 5. 错误类型系统

**目标**: 定义异常层次结构

```
APIError
├── AuthenticationError (401)
├── RateLimitError (429)
├── ModelNotFoundError (404)
├── ServerError (5xx)
└── TimeoutError
```

**在 tester 中精确捕获和分类**

---

#### 6. 解耦日志系统

**目标**: 引入 EventBus 或信号槽机制

**业务逻辑 emit 事件，logger subscribe 事件**

**支持多个监听器**: 控制台、文件、数据库、Slack

---

### P2 - 改进（增强能力）

#### 7. 爬虫鲁棒性

- 选择器版本管理（v1/v2/v3）
- 页面结构变化检测和告警
- 备用数据源（API 直接获取模型列表）

---

#### 8. 测试覆盖率

- 核心模块单元测试 ≥80%
- 集成测试（真实 API 调用，使用 mock）
- CI/CD 自动化测试流水线

---

#### 9. 报告定制化

- 支持 Jinja2 模板
- 可选输出格式：HTML, PDF, CSV
- 用户自定义字段和排序规则

---

### P3 - 锦上添花（长期规划）

#### 10. Web UI

- Flask/FastAPI 提供 Web 界面
- 实时查看测试进度
- 历史报告浏览和对比

---

#### 11. 数据库存储

- SQLite 存储历史测试结果
- 趋势分析和模型稳定性评估
- API 响应时间变化追踪

---

#### 12. 插件系统

- 支持第三方平台插件
- 自定义测试脚本
- 可扩展的报告后处理器

---

## 关键文件索引

| 文件路径 | 行数 | 核心职责 | 重要程度 |
|---------|------|---------|---------|
| src/base_client.py | 116 | 抽象客户端基类 | ⭐⭐⭐⭐⭐ |
| src/nvidia_client.py | 191 | NVIDIA API 客户端 | ⭐⭐⭐⭐⭐ |
| src/platform_registry.py | 240 | 平台注册表（单例+装饰器） | ⭐⭐⭐⭐⭐ |
| src/config_loader.py | 183 | 配置加载器 | ⭐⭐⭐⭐ |
| src/ssl_config.py | 38 | SSL 证书配置 | ⭐⭐⭐ |
| crawler/scraper.py | 862 | Playwright 爬虫（最复杂） | ⭐⭐⭐⭐⭐ |
| crawler/tester.py | 316 | 批量测试引擎 | ⭐⭐⭐⭐⭐ |
| crawler/logger.py | 246 | 日志和断点续传 | ⭐⭐⭐⭐ |
| crawler/main.py | 152 | CLI 入口 | ⭐⭐⭐⭐ |
| crawler/models.py | 123 | 爬虫数据模型 | ⭐⭐⭐⭐ |
| report/generator.py | 192 | 报告生成器 | ⭐⭐⭐⭐ |
| platforms/zhipu/client.py | 81 | 智谱 API 客户端 | ⭐⭐⭐ |
| configs/platforms.yaml | 148 | 平台配置文件 | ⭐⭐⭐ |

**复杂度排名** (按代码行数和维护难度):
1. scraper.py (862行) - 最复杂，包含 Playwright 自动化和解析逻辑
2. platform_registry.py (240行) - 设计模式密集
3. nvidia_client.py (191行) - 平台实现的核心
4. tester.py (316行) - 并发控制和错误处理
5. config_loader.py (183行) - 多级配置回退

---

## 扩展指南（给其他 AI 的提示）

### 如何添加新平台

**步骤清单**:

1. 在 `platforms/{name}/` 创建目录
2. 实现 client.py（继承 BaseClient 或 BasePlatformClient）
3. 如果需要爬虫：实现 scraper.py（继承 BaseScraper）
4. 如果需要测试：实现 tester.py（继承 BaseTester）
5. 使用 `@register_platform` 装饰器注册
6. 在 `configs/platforms.yaml` 添加配置
7. 更新 `ConfigLoader.ENV_VAR_MAP`

**示例代码模板**:

```python
# platforms/newplatform/client.py
from src.base_client import BaseClient
from src.platform_registry import register_platform
from openai import OpenAI

@register_platform(name="newplatform", api_key_env="NEWPLATFORM_API_KEY")
class NewPlatformClient(BaseClient):
    BASE_URL = "https://api.newplatform.com/v1"

    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            base_url=self.BASE_URL,
            api_key=api_key
        )

    def chat(self, messages, **kwargs):
        response = self.client.chat.completions.create(
            model=kwargs.get("model", "default-model"),
            messages=[{"role": m.role, "content": m.content} for m in messages]
        )
        return ChatMessage(
            role="assistant",
            content=response.choices[0].message.content
        )

    def list_models(self):
        response = self.client.models.list()
        return [
            ModelInfo(
                model_id=model.id,
                name=model.id.split("/")[-1]
            )
            for model in response.data
        ]

    def test_connection(self) -> bool:
        try:
            models = self.list_models()
            return len(models) > 0
        except Exception:
            return False
```

**配置文件示例**:

```yaml
# configs/platforms.yaml
newplatform:
  display_name: "New Platform"
  base_url: "https://api.newplatform.com/v1"
  free_models:
    - "model-a"
    - "model-b"
  rate_limits:
    requests_per_minute: 60
    tokens_per_minute: 40000
  features:
    - streaming
    - function_calling
    - vision
```

---

### 如何修改爬虫选择器

**步骤清单**:

1. 定位 `crawler/scraper.py` 的 `_extract_models()` 方法
2. 修改 `query_selector_all()` 的 CSS/XPath 选择器
3. 更新字段提取逻辑（model_name, vendor, tags, category）
4. 测试：`python crawler/main.py --scrape-only -n 5`
5. 如果页面结构大变：考虑增加版本号和 fallback

**常见调整场景**:

```python
# 场景1: NVIDIA 更改了 model card 的 data-testid
# 旧: '[data-testid="nv-card-root"]'
# 新: '[data-testid="model-card"]'

cards = await page.query_selector_all('[data-testid="model-card"]')

# 场景2: Category Tag 从第5行变为第3行
# 旧: lines[4]
# 新: lines[2]

category_tag = lines[2] if len(lines) > 2 else ""

# 场景3: 添加新的标签提取逻辑
is_flash_model = "flash" in model_name.lower()
if is_flash_model:
    tags.append("flash")
```

**调试技巧**:

```bash
# 使用 Playwright 的截图功能调试
await page.screenshot(path="debug_page.png")

# 打印页面 HTML 结构
html = await page.content()
print(html[:2000])  # 前2000字符

# 在浏览器中交互式调试（非 headless 模式）
browser = await playwright.chromium.launch(headless=False)  # 显示浏览器窗口
```

---

### 如何调整测试策略

**步骤清单**:

1. 修改 `crawler/tester.py` 的 `test_single_model()` 方法
2. 调整测试 prompt（当前："请回复'OK'"）
3. 修改超时时间（默认60秒）
4. 调整并发数（默认3，通过 `-c` 参数）
5. 如需复杂测试：添加新的测试方法并在 batch_test 中调用

**常见调整场景**:

```python
# 场景1: 修改测试 prompt（测试多轮对话能力）
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"},
    {"role": "assistant", "content": "The answer is 4."},
    {"role": "user", "content": "And what is 3+3?"}
]

# 场景2: 增加 token 使用量检查
response = client.chat.completions.create(
    ...,
    max_tokens=100  # 允许更长的回复
)

tokens_used = response.usage.total_tokens
if tokens_used > 1000:
    model.test_result.metadata["high_token_usage"] = True

# 场景3: 测试推理模型（reasoning_content）
if hasattr(response.choices[0].message, "reasoning_content"):
    reasoning = response.choices[0].message.reasoning_content
    model.test_result.metadata["has_reasoning"] = True
    model.test_result.metadata["reasoning_length"] = len(reasoning)

# 场景4: 测试 Function Calling 能力
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {...}
    }
}]

response = client.chat.completions.create(
    ...,
    tools=tools
)

# 检查是否正确调用了 tool_calls
if response.choices[0].message.tool_calls:
    model.test_result.metadata["supports_function_calling"] = True
```

**性能优化建议**:

```python
# 场景5: 自适应超时时间
def get_adaptive_timeout(model: ModelInfo) -> int:
    """根据模型大小和历史表现动态调整超时"""
    base_timeout = 60

    # 大模型通常更慢
    if any(size in model.model_id.lower() for size in ["70b", "100b", "400b"]):
        base_timeout *= 2

    # Flash 模型通常更快
    if "flash" in model.name.lower():
        base_timeout //= 2

    # 历史数据：如果上次超时，增加 50%
    last_result = db.get_last_test_result(model.model_id)
    if last_result and last_result.status == "timeout":
        base_timeout = int(base_timeout * 1.5)

    return base_timeout

# 场景6: 智能重试策略
async def test_with_retry(model, max_retries=3):
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            result = await test_single_model(model)
            if result.test_result.status == "success":
                return result
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * e.retry_after or 5
                print(f"Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
            else:
                raise
```

---

## 附录

### A. 常用命令速查

```bash
# 基础用法
python crawler/main.py -n 20                          # 测试 20 个热门模型
python crawler/main.py -n 50 -c 5                     # 50个模型，并发数5
python crawler/main.py --sort-by recent -n 50          # 测试最新发布的模型

# 调试模式
python crawler/main.py --scrape-only -n 30             # 仅爬取不测试
python crawler/main.py --resume -n 50                  # 断点续传
python crawler/main.py --no-filter -n 20               # 不过滤非文字模型
python crawler/main.py --no-log -n 10                  # 禁用日志系统

# 性能调优
python crawler/main.py -n 100 -c 5 --timeout 120       # 大规模测试
python crawler/main.py --sort-by popular -n 200         # 按热度爬取更多模型
```

### B. 环境变量列表

| 变量名 | 用途 | 示例值 | 是否必需 |
|-------|------|--------|---------|
| `NVIDIA_API_KEY` | NVIDIA API 密钥 | `nvapi-xxxxx` | ✅ 是 |
| `ZHIPU_API_KEY` | 智谱 API 密钥 | `xxxxx.xxxxx` | ⚠️ 可选 |
| `SSL_CERT_FILE` | SSL 证书路径 | `/path/to/cert.pem` | ❌ 否 |
| `REQUESTS_CA_BUNDLE` | CA 证书包路径 | `/path/to/ca-bundle.crt` | ❌ 否 |
| `VERIFY_SSL` | 是否验证 SSL | `true`/`false` | ❌ 否（默认 true） |

### C. 项目目录结构（完整版）

```
api_key_test/
├── src/                        # 基础层：接口和数据结构
│   ├── __init__.py
│   ├── base_client.py          # 抽象客户端基类
│   ├── nvidia_client.py        # NVIDIA API 客户端
│   ├── platform_registry.py    # 平台注册表（单例+装饰器）
│   ├── config_loader.py        # 配置加载器
│   ├── ssl_config.py           # SSL 证书配置
│   └── models.py               # 数据类定义
│
├── platforms/                  # 平台层：具体实现
│   ├── __init__.py
│   ├── base/                   # 平台基类
│   │   ├── __init__.py
│   │   ├── base_scraper.py     # 爬虫抽象基类
│   │   ├── base_tester.py      # 测试器抽象基类
│   │   └── base_client.py      # 客户端抽象基类
│   └── zhipu/                  # 智谱平台
│       ├── __init__.py
│       └── client.py           # 智谱 API 客户端
│
├── crawler/                    # 应用层：业务逻辑
│   ├── __init__.py
│   ├── scraper.py              # Playwright 爬虫（核心）
│   ├── tester.py               # 批量测试引擎
│   ├── logger.py               # 日志和断点续传
│   ├── main.py                 # CLI 入口
│   └── models.py               # 爬虫数据模型
│
├── report/                     # 报告层：可视化输出
│   ├── __init__.py
│   └── generator.py            # 报告生成器
│
├── configs/                    # 配置文件
│   └── platforms.yaml          # 平台配置
│
├── docs/                       # 输出文档
│   ├── nvidia/                 # NVIDIA 测试报告
│   ├── zhipu/                  # 智谱测试报告
│   ├── raw-data/               # JSON 原始数据
│   │   ├── nvidia/
│   │   └── zhipu/
│   └── PROJECT_PRINCIPLES.md   # 本文档
│
├── tests/                      # 单元测试（待完善）
│   └── __init__.py
│
├── logs/                       # 运行日志
│   ├── *.jsonl                 # JSON Lines 日志
│   └── checkpoint.json         # 断点续传状态
│
├── .env.local                  # 本地环境变量（不提交）
├── .gitignore                  # Git 忽略规则
├── CLAUDE.md                   # AI 助手规则
└── README.md                   # 项目说明
```

### D. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|-----|------|------|---------|
| 1.0.0 | 2026-04-24 | AI Assistant | 初始版本，完整项目原理文档 |

### E. 参考资料

- [Playwright 官方文档](https://playwright.dev/python/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [NVIDIA API 文档](https://build.nvidia.com/explore/discover)
- [智谱开放平台](https://open.bigmodel.cn/)
- [Python 设计模式](https://refactoring.guru/design-patterns/python)

---

## 结语

本文档旨在为项目维护者和后续开发者提供全面的技术参考。通过清晰的架构说明、设计模式解释和实用的扩展指南，希望能够：

✅ **降低上手门槛** - 新开发者快速理解项目结构  
✅ **提高重构效率** - 明确技术债务和优先级  
✅ **保证扩展质量** - 提供标准化的扩展流程  
✅ **促进知识传承** - 减少关键信息的丢失  

如有任何疑问或建议，欢迎更新本文档或联系维护者。

---

**最后更新**: 2026-04-24  
**文档版本**: 1.0.0  
**适用项目版本**: v2.0+
