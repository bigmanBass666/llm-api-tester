# API 模型测试工具

**一句话介绍**：爬取并测试 NVIDIA、智谱等平台免费 AI 模型的一站式工具，生成可视化测试报告。

**适用场景**：
- 🤖 寻找可免费使用的 AI 模型
- 📊 对比各模型的响应速度和稳定性
- 🔍 发现新发布的高质量模型
- ✅ 测试模型是否正常工作

---

## ⚡ 快速上手（3步搞定）

### 第一步：安装依赖

```bash
# 克隆项目
cd api_key_test

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（仅爬虫功能需要）
playwright install chromium
```

### 第二步：配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env.local

# 编辑 .env.local，填入你的 API Key
# NVIDIA_API_KEY=nvapi-你的密钥
```

> 💡 **免费获取 NVIDIA API Key**：访问 [build.nvidia.com](https://build.nvidia.com)，用 GitHub 账号登录即可获取免费密钥。

### 第三步：开始使用

```bash
# 场景1：测试 10 个热门模型（最常用）
python crawler/main.py -n 10

# 场景2：查看所有可用模型（不测试）
python crawler/main.py --scrape-only -n 20

# 场景3：测试最新发布的模型（而非按热度）
python crawler/main.py -n 20 --sort-by recent

# 场景4：提高并发加速测试（默认3）
python crawler/main.py -n 20 -c 5
```

---

## 🎯 核心功能

### 1️⃣ 爬取模型列表
```bash
python crawler/main.py --scrape-only -n 50
```
- 按官方热度排序爬取前 N 个模型
- 自动过滤语音/图像等非文字模型
- 支持按热度（popular）或最新（recent）排序

### 2️⃣ 批量测试模型
```bash
python crawler/main.py -n 20 -c 3
```
- 并发测试多个模型（默认3个同时）
- 自动记录响应时间、超时、错误
- 支持断点续传（中途中断了可以继续）

### 3️⃣ 生成测试报告
```bash
# 测试完成后，报告自动生成在：
# - docs/nvidia/NVIDIA_BATCH_TEST_日期时间.md  (Markdown 格式，可读性好)
# - docs/raw-data/nvidia/nvidia_raw_日期时间.json  (原始数据)
```

---

## 📋 常用命令速查

| 需求 | 命令 |
|------|------|
| 测试前10个热门模型 | `python crawler/main.py -n 10` |
| 仅查看模型列表 | `python crawler/main.py --scrape-only -n 20` |
| 测试最新模型 | `python crawler/main.py -n 20 --sort-by recent` |
| 提高并发加速 | `python crawler/main.py -n 20 -c 5` |
| 增加超时时间 | `python crawler/main.py -n 20 --timeout 120` |
| 断点续传（继续上次） | `python crawler/main.py -n 50 --resume` |
| 查看所有参数 | `python crawler/main.py --help` |

---

## 💬 编程接口（Python 代码调用）

### 方式一：一行代码调用

```python
from src.nvidia_client import nvidia_chat

# 直接发送消息，自动处理 API Key
result = nvidia_chat("minimax-m2.7", "请回复 OK")
print(result)
```

### 方式二：创建客户端

```python
from src.nvidia_client import NvidiaClient

client = NvidiaClient()

# 使用完整模型 ID
result = client.chat(
    "minimaxai/minimax-m2.7",
    [{"role": "user", "content": "写一个 Hello World"}]
)
print(result)

client.close()
```

### 方式三：统一接口（推荐用于多平台）

```python
from src import use_platform, chat

# 设置默认平台
use_platform("nvidia")

# 统一调用不同平台的模型
result = chat("minimaxai/minimax-m2.7", "你好")
print(result)
```

---

## 🔧 进阶用法

### 调整并发数
```bash
# -c 参数控制同时测试的模型数量
# 默认 3，太高可能触发 API 限流
python crawler/main.py -n 50 -c 5
```

### 自定义超时时间
```bash
# 网络慢时增大超时（秒）
python crawler/main.py -n 20 --timeout 120
```

### 断点续传
```bash
# 如果测试中途按 Ctrl+C 中断了
# 下次运行时加 --resume 可以跳过已测试的模型
python crawler/main.py -n 50 --resume
```

### 过滤非文字模型
```bash
# 默认会过滤掉语音、图像、嵌入等非文字模型
# 如果想测试所有模型（包括嵌入模型等）：
python crawler/main.py -n 20 --no-filter
```

---

## ❓ 常见问题

### Q: 报 "请设置 NVIDIA_API_KEY" 错误
**A**: 你需要创建 `.env.local` 文件并填入 API Key：
```bash
cp .env.example .env.local
# 然后编辑 .env.local
```

### Q: 报 SSL 证书错误
**A**: 项目已配置自动处理 SSL，如果仍有问题，尝试：
```bash
# 设置环境变量
set SSL_CERT_FILE=/path/to/certifi/cacert.pem
```

### Q: 爬虫返回空列表或很少模型
**A**: NVIDIA 网站可能改版或网络问题，尝试：
```bash
# 减少每次请求的模型数量
python crawler/main.py --scrape-only -n 10
# 或者换个时间再试
```

### Q: 测试时大量超时
**A**: 某些模型确实响应慢，尝试：
```bash
# 增大超时时间
python crawler/main.py -n 20 --timeout 120
# 或者跳过不稳定的模型（已有报告会自动记录）
```

### Q: 如何测试智谱模型？
**A**: 智谱客户端已部分实现，但爬虫主要针对 NVIDIA：
```python
from platforms.zhipu import ZhipuClient

client = ZhipuClient(api_key="你的智谱APIKey")
result = client.chat("glm-4-flash-250414", [{"role": "user", "content": "你好"}])
print(result)
```

### Q: 什么是推理模型？如何测试？
**A**: 推理模型（如 DeepSeek V4、GLM-5.1）需要特殊的调用参数才能正常工作：

```bash
# 自动检测并使用推理模式测试 DeepSeek V4
python crawler/main.py -n 10 --sort-by recent

# 手动指定推理模型
python crawler/main.py -n 10 --reasoning-model deepseek-ai/deepseek-v4-flash

# 推理模型使用更长的超时时间（默认180秒）
```

**推理模型 vs 普通模型的区别**：

| 特性 | 普通模型 | 推理模型 |
|------|---------|----------|
| 示例 | Qwen3 Coder, MiniMax M2 | DeepSeek V4, GLM-5.1 |
| extra_body | 不需要 | `{"chat_template_kwargs":{"thinking":True}}` |
| stream | 可选 | **必须** |
| 响应字段 | `delta.content` | `delta.reasoning` + `delta.content` |
| 超时时间 | 默认 60s | 默认 180s |

系统会自动识别推理模型，也支持手动指定。

---

## 📁 项目结构

```
api_key_test/
├── src/                          # 核心代码
│   ├── nvidia_client.py         # NVIDIA API 客户端
│   ├── zhipu_client.py          # 智谱 API 客户端
│   ├── base_client.py           # 客户端基类（抽象接口）
│   ├── platform_registry.py     # 平台注册表
│   └── config_loader.py         # 配置加载器
│
├── crawler/                      # 爬虫+测试模块
│   ├── main.py                  # 命令行入口 ⭐（主要使用入口）
│   ├── scraper.py               # 页面爬虫（Playwright）
│   ├── tester.py                # 批量测试引擎
│   └── logger.py                # 日志和断点续传
│
├── report/                       # 报告生成
│   └── generator.py             # Markdown/JSON 双格式输出
│
├── configs/
│   └── platforms.yaml           # 平台配置文件
│
├── docs/                         # 文档和报告
│   ├── PROJECT_PRINCIPLES.md   # 项目原理文档（给 AI 看的）
│   └── nvidia/                  # 测试报告输出目录
│
└── examples/                     # 示例代码
    └── *.py                     # 各种模型调用示例
```

---

## 📊 输出示例

测试完成后，你会得到这样的 Markdown 报告：

```markdown
# NVIDIA 模型批量测试报告

## 📊 总体统计
| 指标 | 数值 |
|------|------|
| 总模型数 | 20 |
| 成功 | 16 ✅ |
| 失败 | 2 ❌ |
| 超时 | 2 ⏰ |
| 成功率 | 80% |

## 🏆 最快模型排行榜
| 排名 | 模型ID | 响应时间 |
|------|--------|----------|
| 1 | qwen/qwen3-coder-480b-a35b-instruct | 1.23s |
| 2 | deepseek-ai/deepseek-v3.1-terminus | 1.45s |

## 🎯 完整测试结果
| 热度排名 | 模型ID | 状态 |
|----------|--------|------|
| #1 | qwen/qwen3-coder-480b... | ✅ 成功 |
| #2 | google/gemma-4-31b-it | ✅ 成功 |
| #3 | z-ai/glm5 | ⏰ 超时 |
```

---

## 🔗 相关文档

- [项目原理文档](docs/PROJECT_PRINCIPLES.md) - 给 AI 重构用的详细技术文档
- [NVIDIA 测试记录](docs/nvidia/) - 历史测试报告
- [平台配置说明](configs/platforms.yaml) - 支持的平台列表

---

**最后更新**: 2026-04-25
