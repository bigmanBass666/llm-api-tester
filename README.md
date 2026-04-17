# API Testing Framework - 多平台 API 测试框架

**用途**: 测试和管理多个平台的 AI API（NVIDIA、阿里云、腾讯云、智谱等）
**维护**: 长期项目，持续更新

---

## 📁 项目结构

```
api_key_test/
├── configs/                      # 配置文件
│   └── platforms.yaml            # 平台配置
├── docs/                         # 文档目录
│   └── NVIDIA_免费模型测试记录.md
├── platforms/                    # 平台特定代码（占位）
│   ├── nvidia/                   # NVIDIA 平台
│   ├── aliyun/                   # 阿里云平台
│   ├── tencent/                  # 腾讯云平台
│   └── zhipu/                    # 智谱平台
├── scripts/                      # 实用脚本
│   └── batch_test.py             # 批量测试
├── src/                          # 核心源代码
│   ├── __init__.py               # 包入口
│   ├── base_client.py            # 客户端基类
│   ├── platform_registry.py      # 平台注册表
│   └── nvidia_client.py          # NVIDIA 客户端
├── crawler/                      # 爬虫架构（新增）
│   ├── main.py                   # 主入口
│   ├── models.py                 # 模型数据结构
│   ├── scraper.py                # NVIDIA 页面爬虫
│   ├── tester.py                 # 批量测试器
│   ├── requirements.txt          # 依赖列表
│   ├── README.md                 # 爬虫文档
│   └── reports/                  # 测试报告
├── tests/                        # 测试用例
├── .mcp.json                     # MCP 配置
└── README.md                     # 本文件
```

---

## ✅ 支持的平台

### NVIDIA NIM ✅ 已实现

| 功能 | 状态 |
|------|------|
| 基础 API 调用 | ✅ 正常 |
| **爬虫批量测试** | ✅ **新增** |
| 按热度排序测试 | ✅ **新增** |
| 异步并发测试 | ✅ **新增** |

**已测试模型**:
- Qwen3 Coder 480B ✅
- MiniMax M2.7 ✅
- DeepSeek V3.1 ✅
- Llama 4 Maverick ✅
- Kimi K2 ✅
- Gemma 7B ✅
- Phi-3 Mini ✅
- Step 3.5 Flash ⚠️
- GLM 4.7 ⚠️
- Qwen 3.5 122B ✅

### 其他平台 🔜 待实现

- [ ] 阿里云百炼 (dashscope)
- [ ] 腾讯云混元
- [ ] 智谱 GLM
- [ ] Ollama (本地)
- [ ] OpenAI (需要代理)

---

## 🚀 快速开始

### 1. 使用 NVIDIA 模型

```python
from src.nvidia_client import nvidia_chat, NvidiaClient

# 方式一：一行代码快速调用
result = nvidia_chat("minimax-m2.7", "你好")

# 方式二：创建客户端
client = NvidiaClient()
result = client.quick_chat("qwen3-coder", "写个 Hello World")
client.close()
```

### 2. 使用统一接口

```python
from src import use_platform, chat

# 设置默认平台
use_platform("nvidia", api_key="your-nvidia-api-key")

# 统一调用
result = chat("minimaxai/minimax-m2.7", "你好")
```

### 3. 批量测试

```bash
# 传统批量测试
python scripts/batch_test.py --platform nvidia

# 🆕 爬虫批量测试（按热度排序）
python crawler/main.py -n 20 -c 5

# 仅爬取模型列表
python crawler/main.py --scrape-only -n 30
```

### 4. 添加新平台

参考 `src/nvidia_client.py` 实现新的平台客户端：

```python
from src import BaseClient, register_platform, ChatMessage

@register_platform(
    name="myplatform",
    display_name="My Platform",
    client_class=None,
    default_base_url="https://api.myplatform.com",
    api_key_env="MYPLATFORM_API_KEY"
)
class MyPlatformClient(BaseClient):
    def chat(self, model, messages, **kwargs):
        # 实现聊天接口
        pass

    def list_models(self):
        # 实现获取模型列表
        pass

    def test_connection(self):
        # 实现连接测试
        pass
```

---

## 📝 配置文件

平台配置位于 `configs/platforms.yaml`，包含：
- 平台基础 URL
- API Key 环境变量名
- 可用模型列表

---

## 🔧 环境变量

```bash
# NVIDIA
export NVIDIA_API_KEY="nvapi-..."

# 阿里云
export DASHSCOPE_API_KEY="..."

# 腾讯云
export TENCENTCLOUD_SECRET_ID="..."
export TENCENTCLOUD_SECRET_KEY="..."

# 智谱
export ZHIPU_API_KEY="..."
```

---

## 📋 开发指南

### 添加新平台

1. 在 `platforms/` 下创建平台目录
2. 参考 `src/nvidia_client.py` 实现客户端类
3. 使用 `@register_platform` 装饰器注册
4. 更新 `configs/platforms.yaml`

### 添加新模型测试

1. 在对应平台的目录下创建测试文件
2. 更新 `docs/模型测试记录.md`

---

**最后更新**: 2026-04-13