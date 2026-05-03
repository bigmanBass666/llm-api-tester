# API 测试项目 Git 自动化管理

## Git 自动化规则

### 1. 会话开始前
- **必须**读取最近 5 条 git 提交记录：`git log --oneline -5`
- 了解项目当前状态和最近修改

### 2. 任务完成后
- **必须**执行本地 git 提交流程（**不自动 push**）：
  1. `git status` 查看变更
  2. `git diff` 检查具体修改
  3. `git add <相关文件>` 添加变更
  4. `git commit -m "描述任务完成内容"` 提交

### 2.1. Push 策略
- **提交后不自动 push**
- 需要推送时，手动执行：
  ```bash
  # 检查当前分支
  git branch --show-current
  # 确认无误后 push
  git push
  ```
- 如果使用功能分支 (`feature/xxx` 或 `bugfix/xxx`)，push 后创建 PR 合并到 `dev` 或 `main`

### 3. 提交信息格式
```
<类型>: <简要描述>

<详细说明>

类型说明:
- feat: 新功能或模型测试
- test: 模型测试结果
- fix: 修复问题
- docs: 文档更新
- refactor: 代码重构
```

### 4. 文件管理原则
- 测试代码和配置文件必须提交
- API keys 和敏感信息必须忽略（已在 .gitignore）
- 临时文件不提交

### 5. 分支策略
- 主分支：`main`
- 功能分支：`feature/<功能名>`
- 修复分支：`bugfix/<问题>`

---

## 当前项目结构

```
api_key_test/
├── src/                         # 核心基础模块
│   ├── __init__.py
│   ├── config_loader.py         # 环境配置加载
│   ├── models.py                # 统一数据模型
│   ├── platform_registry.py     # 平台注册中心
│   └── ssl_config.py            # SSL 证书配置
│
├── platforms/                   # 各平台独立模块（分层架构）
│   ├── base/                    # 平台基类（定义接口）
│   │   ├── __init__.py
│   │   ├── base_client.py       # API 客户端基类
│   │   ├── base_scraper.py      # 爬虫基类
│   │   └── base_tester.py       # 测试器基类
│   │
│   ├── nvidia/                  # NVIDIA 平台实现
│   │   ├── __init__.py
│   │   ├── client.py            # NVIDIA API 客户端
│   │   ├── scraper.py           # NVIDIA 页面爬虫
│   │   └── tester.py            # NVIDIA 模型测试器
│   │
│   └── zhipu/                   # 智谱平台实现
│       ├── __init__.py
│       ├── client.py            # 智谱 API 客户端
│       ├── scraper.py           # 智谱页面爬虫
│       └── tester.py            # 智谱模型测试器
│
├── crawler/                     # 旧版爬虫系统（兼容保留）
│   ├── main.py                  # 主入口程序
│   ├── models.py                # 模型数据结构
│   ├── scraper.py               # 页面爬虫
│   ├── tester.py                # 批量测试器
│   ├── speed_tester.py          # 速度测试器
│   ├── simple_tester.py         # 简易测试器
│   ├── logger.py                # 日志模块
│   ├── errors.py                # 异常定义
│   ├── requirements.txt         # 依赖配置
│   └── reports/                 # 测试报告目录
│
├── report/                      # 报告生成模块（新版）
│   ├── __init__.py
│   └── generator.py             # 报告生成器
│
├── configs/                     # 配置文件
│   └── platforms.yaml           # 平台配置
│
├── scripts/                     # 入口脚本
│   ├── batch_test.py            # 批量测试脚本
│   ├── test_nvidia.py           # NVIDIA 测试入口
│   ├── test_zhipu.py            # 智谱测试入口
│   ├── test_flux_image.py       # 图像生成测试
│   └── setup_env.py             # 环境设置
│
├── tests/                       # 测试套件
│   ├── __init__.py
│   ├── conftest.py              # pytest 配置
│   ├── test_models.py           # 模型测试
│   ├── test_registry.py         # 注册中心测试
│   ├── test_tester.py           # 测试器测试
│   ├── test_errors.py           # 异常测试
│   ├── test_reasoning_models.py # 推理模型测试
│   └── test_speed_tester_framework.py # 速度测试框架
│
├── examples/                    # 示例代码
│   ├── README.md
│   ├── base_example.py
│   ├── gemma_4_31b_it.py
│   ├── glm4_7.py
│   ├── glm5.py
│   └── ...
│
├── docs/                        # 文档输出
│   ├── nvidia/                  # NVIDIA 测试报告
│   ├── zhipu/                   # 智谱测试报告
│   ├── platforms/               # 平台相关文档
│   ├── raw-data/                # JSON 原始数据
│   ├── API_KEY_SETUP.md
│   ├── ARCHITECTURE.md          # 架构蓝图
│   ├── REFACTOR_PRINCIPLES.md   # 重构原则
│   └── ...
│
├── AGENTS.md                    # 本文件（Agent 工作指南）
└── README.md                    # 项目主文档
```

---

## 测试流程

### 基础测试流程
1. 先检查模型是否在 `/v1/models` 列表中
2. 测试简单对话（"回复 OK"）
3. 记录响应时间和输出格式
4. 更新测试文档
5. 提交 git

### 爬虫批量测试流程（旧版 crawler/）

#### 1. 选择排序方式
NVIDIA 爬虫支持两种排序方式：
- **热度排序**（`--sort-by popular`，默认）：按官方热度权重排序，适合发现稳定、常用的模型
- **最新排序**（`--sort-by recent`）：按发布时间排序，可爬到最新模型（如 GLM-5.1 会排在第1位）

#### 2. 开始爬取
```bash
# 使用热度排序（默认）
python crawler/main.py -n 50

# 使用最新排序
python crawler/main.py -n 50 --sort-by recent
```

爬虫必须提取模型卡片标签：
- 📥 **downloadable** - 模型权重可下载
- 🔓 **free** - 免费API端点
- ⏰ **timeout** - 无法访问

#### 3. 批量测试所有爬取的模型（并发3-5）
#### 4. 记录每个模型的：
- 热度排名（rank）
- 响应时间（response_time）
- 标签信息（is_downloadable, is_free_endpoint, tags）
- 是否可调用（test_status）

#### 5. 生成 Markdown 报告
报告文件（`docs/nvidia/NVIDIA_BATCH_TEST_YYYYMMDD_HHMMSS.md`）必须包含：
- 📈 总体统计（成功率）
- 🏆 最快模型排行榜（Top 10，含标签）
- 🎯 完整测试结果（按实际排序方式显示，标注标签）
- 🔍 爬取信息和原始数据链接

#### 6. 保存 JSON 原始报告
包含完整标签数据，同样带时间戳（`docs/raw-data/nvidia/nvidia_raw_YYYYMMDD_HHMMSS.json`）

#### 7. 提交所有报告文件和更新代码

### 新版平台测试流程（platforms/）

#### 1. 使用平台客户端
```python
from platforms.nvidia import NvidiaClient

# 创建客户端
client = NvidiaClient(api_key="your-api-key")

# 列出模型
models = client.list_models()

# 测试对话
response = client.chat(
    model="qwen/qwen3-coder-480b-a35b-instruct",
    messages=[{"role": "user", "content": "Hello"}]
)
```

#### 2. 使用平台爬虫
```python
from platforms.nvidia import NvidiaScraper

scraper = NvidiaScraper()
models = await scraper.scrape(limit=50)
```

#### 3. 使用平台测试器
```python
from platforms.nvidia import NvidiaTester

tester = NvidiaTester()
results = await tester.batch_test(models, concurrency=3)
```

---

## 报告格式规则

### Markdown 报告表格必须包含的列
| 热度排名 | 模型ID | 标签 | 响应时间 | 是否可调用/错误详情 |
|----------|--------|------|----------|-------------------|

### 标签映射表
| 图标 | 标签名 | 含义 |
|------|--------|------|
| 📥 | downloadable | 模型权重可下载 |
| 🔓 | free | 免费API端点 |
| ❌ | unknown/timeout | 无法访问或超时 |

### 推荐模型标注
报告中必须标注：
- ✅ **推荐使用的模型**（速度快+稳定+标签清晰）
- ❌ **避免使用的模型**（持续超时或不可用）

---

## 注意事项

- NVIDIA API 需要 SSL 证书设置
- 推理模型输出在 `reasoning_content`
- 流式响应需要特殊处理
- 每次测试后必须更新文档
- 爬虫必须使用 `--ignore-certificate-errors` 规避 SSL 问题
- **分层架构**: 新版代码使用 `platforms/` 目录，旧版 `crawler/` 保留兼容
- **基类系统**: 所有平台实现必须继承 `platforms/base/` 中的基类
