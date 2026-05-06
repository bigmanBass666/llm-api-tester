<h1 align="center">🧪 LLM API Tester</h1>

<p align="center">
  <strong>多平台大模型 API 测试与基准评测工具</strong>
</p>

<p align="center">
  <a href="#功能特性">特性</a> •
  <a href="#支持平台">平台</a> •
  <a href="#快速开始">开始</a> •
  <a href="#项目结构">结构</a> •
  <a href="#使用示例">示例</a> •
  <a href="#开发指南">开发</a>
</p>

---

## ✨ 功能特性

- **多平台支持** — 统一接口测试 NVIDIA NIM、智谱 GLM、阿里云百炼、腾讯云混元、OpenAI、DeepSeek、Ollama 等 LLM 平台
- **免费模型覆盖** — 内置各平台免费/开源模型列表，开箱即用
- **自动化爬虫** — 基于 Playwright 自动从 NVIDIA build.nvidia.com 和智谱官网抓取最新可用模型
- **并发压力测试** — 可配置并发数，批量测试模型响应时间与成功率
- **推理模型适配** — 原生支持 Reasoning 模型（GLM-4.7、Step 3.5 Flash 等）的特殊请求格式
- **图像生成测试** — 支持 Flux、Stable Diffusion 等图像生成模型 API 调用
- **速度基准评测** — 多维度性能指标采集（响应时间 P50/P95/P99、Token 吞吐量）
- **报告自动生成** — JSON 格式结构化测试报告，含成功率和耗时统计
- **YAML 驱动配置** — `configs/platforms.yaml` 作为唯一数据源，新增平台只需编辑 YAML + 编写适配器
- **SSL 自动处理** — 内置 Windows SSL 证书兼容方案，解决 certifi 问题
- **安全扫描** — 集成 detect-secrets baseline，防止密钥泄露

---

## 🌐 支持平台

| 平台 | 状态 | 免费模型 | 特色 |
|------|:----:|---------|------|
| **NVIDIA NIM** | ✅ 可用 | Qwen3 Coder 480B / DeepSeek V3.1 / Llama 4 Maverick / Kimi K2 / MiniMax M2.7 等 | 开源模型最全，含图像生成 |
| **智谱 AI (GLM)** | ✅ 可用 | GLM-4 Flash / GLM-4V Flash / GLM-4.7 Flash / CogView-3 / CogVideoX 等 | 200 并发免费 API，128K 上下文 |
| **阿里云百炼** | 🔒 待启用 | 通义千问 Turbo / Plus / Max | - |
| **腾讯云混元** | 🔒 待启用 | 混元系列 | - |
| **OpenAI** | 🔒 待启用 | GPT 系列 | 需代理 |
| **DeepSeek** | 🔒 待启用 | DeepSeek V3 / R1 | - |
| **Ollama** | 🔒 本地 | Llama 3 / Mistral / Code Llama | 本地部署 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+

### 安装依赖

```bash
git clone https://github.com/bigmanBass666/llm-api-tester.git
cd llm-api-tester
pip install -r requirements.txt
```

### 配置 API Key

```bash
cp .env.example .env.local
# 编辑 .env.local，填入你的 API Key
```

支持的環境变量：

| 变量名 | 平台 | 获取地址 |
|--------|------|----------|
| `NVIDIA_API_KEY` | NVIDIA NIM | https://build.nvidia.com |
| `ZHIPU_API_KEY` | 智谱 AI | https://www.bigmodel.cn/usercenter/proj-mgmt/rate-limits |
| `DASHSCOPE_API_KEY` | 阿里云百炼 | https://bailian.console.aliyun.com/ |
| `TENCENTCLOUD_SECRET_ID` / `_SECRET_KEY` | 腾讯云混元 | https://console.cloud.tencent.com/cam/capi |

### 运行测试

```bash
# 快速验证配置
python test_config_quick.py

# 运行 NVIDIA 批量测试
python scripts/run_nvidia.py

# 运行智谱测试（含速度测试）
python scripts/run_zhipu.py
python scripts/run_zhipu_speed.py   # 速度基准测试

# 运行综合测试（所有已启用平台）
python scripts/run_comprehensive.py

# 运行爬虫抓取最新模型
python crawler/main.py -n 10

# 运行单元测试
pytest tests/test_platform_config.py -v

# 图像生成测试
python scripts/run_flux_image.py
```

---

## 📁 项目结构

```
llm-api-tester/
├── configs/
│   └── platforms.yaml          # ← 唯一数据源：所有平台配置与模型列表
├── src/                         # 核心源码
│   ├── models.py                # 数据模型 (ModelInfo, TestResult, TestReport)
│   ├── config_loader.py         # YAML 配置加载器
│   ├── platform_config.py       # 平台配置解析与验证
│   ├── platform_registry.py     # 平台注册表（工厂模式）
│   └── ssl_config.py            # SSL 证书自动配置
├── platforms/                   # 平台适配器（按平台目录隔离）
│   ├── base/                    # 基础抽象类
│   ├── nvidia/                  # NVIDIA NIM 适配器
│   └── zhipu/                   # 智谱 GLM 适配器
├── crawler/                     # Playwright 爬虫模块
│   ├── main.py                  # 爬虫入口
│   ├── scraper.py               # 页面抓取逻辑
│   ├── tester.py                # API 测试引擎
│   ├── speed_tester.py          # 速度基准测试
│   └── simple_tester.py         # 简易测试
├── scripts/                     # 运行脚本
│   ├── run_nvidia.py            # NVIDIA 测试
│   ├── run_zhipu.py             # 智谱测试
│   ├── run_zhipu_speed.py       # 智谱速度测试
│   ├── run_comprehensive.py     # 全平台综合测试
│   ├── run_flux_image.py        # 图像生成测试
│   ├── batch_test.py            # 批量测试框架
│   └── setup_env.py             # 环境检查脚本
├── examples/                    # 使用示例（各模型独立文件）
│   ├── base_example.py          # 基础用法
│   ├── glm4_7.py                # GLM-4.7 推理模型
│   ├── gemma_4_31b_it.py        # Gemma 4 示例
│   ├── minimax_m2_7.py          # MiniMax M2.7 示例
│   ├── qwen3_5_122b_a10b.py     # Qwen3.5 示例
│   └── step_3_5_flash.py        # Step 3.5 Flash 推理模型
├── report/                      # 报告生成模块
│   └── generator.py             # JSON 报告生成器
├── tests/                       # pytest 单元测试
├── docs/                        # 文档与原始数据
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── AGENTS.md                    # AI Agent 协作规范
└── .pre-commit-config.yaml      # Git hooks 配置
```

---

## 💡 使用示例

### 基础调用

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)

response = client.chat.completions.create(
    model="qwen/qwen3-coder-480b-a35b-instruct",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100,
)
print(response.choices[0].message.content)
```

### 使用 ConfigLoader 加载配置

```python
from src.config_loader import ConfigLoader

loader = ConfigLoader()
platforms = loader.get_available_platforms()
for p in platforms:
    print(f"{p.display_name}: {len(p.models)} models")
```

更多示例请查看 [examples/](examples/) 目录。

---

## 🛠️ 开发指南

### 新增平台

1. 在 `configs/platforms.yaml` 中添加平台配置
2. 在 `platforms/{name}/` 目录下创建适配器（继承 base 基类）
3. 在 `src/platform_registry.py` 中注册新平台
4. 运行测试：`pytest tests/test_platform_config.py -v`

### Git 规范

采用 Conventional Commits（中文描述）：

```
<type>: <中文描述>
```

type ∈ `{feat, fix, test, docs, refactor, chore}`

### 核心原则

- **配置唯一数据源**: `configs/platforms.yaml`
- **新代码导入路径**: `platforms/`（禁止直接引用 `crawler/`）
- **修改代码后必测**: `pytest tests/test_platform_config.py -v`
- **禁止** `git add .`，只添加相关文件

---

## 📦 依赖清单

| 包名 | 用途 |
|------|------|
| `openai>=1.0.0` | OpenAI 兼容 SDK |
| `httpx>=0.27.0` | 异步 HTTP 客户端 |
| `python-dotenv>=1.0.0` | 环境变量加载 |
| `playwright>=1.40.0` | 浏览器自动化爬虫 |
| `beautifulsoup4>=4.12.0` | HTML 解析 |
| `pytest>=7.0.0` | 单元测试框架 |
| `tqdm>=4.65.0` | 进度条显示 |
| `pyyaml>=6.0` | YAML 配置解析 |
| `certifi>=2023.0.0` | SSL 证书（Windows 兼容） |

---

## 📄 License

MIT License

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/bigmanBass666">bigmanBass666</a>
</p>