# NVIDIA NIM 模型调用示例

本目录包含 NVIDIA NIM API 的调用示例代码，针对不同特性的模型提供相应的调用方式。

## 快速开始

### 环境准备

```bash
# 安装依赖
pip install openai httpx requests
```

### 设置 API Key

所有示例默认使用硬编码的测试 API Key，实际使用时请修改为：

1. **推荐**：创建 `.env` 文件或设置环境变量 `NVIDIA_API_KEY`
2. **替代**：修改示例代码中的 `api_key` 变量

### SSL 证书

系统会自动使用 certifi 提供的证书，一般无需手动配置。如遇 SSL 错误：

```python
from src.ssl_config import setup_ssl_certificates
setup_ssl_certificates()
```

或通过环境变量指定自定义证书路径：

```bash
# 在 .env.local 中设置
SSL_CERT_FILE=/path/to/your/cert.pem
REQUESTS_CA_BUNDLE=/path/to/your/cert.pem
```

## 模型示例

### 🧠 推理模型

这些模型需要启用 `thinking` 模式：

| 模型 | 示例文件 | 特点 |
|------|----------|------|
| **Google Gemma 4 31B IT** | `gemma_4_31b_it.py` | 需 `enable_thinking=True`，推理内容在 `reasoning_content` |
| **Z.ai GLM 4.7** | `glm4_7.py` | 推理模式，输出在 `reasoning_content` |
| **Step 3.5 Flash** | `step_3_5_flash.py` | 复杂问题可能只输出推理内容 |

运行示例：

```bash
python gemma_4_31b_it.py
python glm4_7.py --stream  # 流式版本
```

### 🤖 普通聊天模型

这些模型输出在 `content` 字段：

| 模型 | 示例文件 | 备注 |
|------|----------|------|
| MiniMax M2.7 | `minimax_m2_7.py` | 响应速度快 |
| **Qwen 3.5 122B A10B** | `qwen3_5_122b_a10b.py` | ✅ 新增，2.9s 快速响应 |
| Qwen3 Coder 480B | `base_example.py` | 编程专用 |
| DeepSeek V3.1 | `base_example.py` | |
| Llama 4 Maverick | `base_example.py` | |
| Kimi K2 | `base_example.py` | |
| Gemma 7B | `base_example.py` | |
| Phi-3 Mini | `base_example.py` | |

### ⚠️ 不可用模型

| 模型 | 示例文件 | 状态 |
|------|----------|------|
| **Z.ai GLM 5** | `glm5.py` | ❌ 连接超时，无法使用 |

## 示例文件说明

### base_example.py

通用模板，支持：

- 非流式调用：`test_model_simple(model_id)`
- 流式调用：`test_model_streaming(model_id, enable_thinking)`

### 模型特定示例

每个模型都有独立的示例文件，包含：

- 针对模型特性的配置
- 完整的错误处理
- 输出格式化说明

## API 参数说明

### 必填参数

```python
{
    "model": "模型ID",
    "messages": [{"role": "user", "content": "你的消息"}],
    "max_tokens": 100,  # 最大生成token数
}
```

### 可选参数

```python
{
    "temperature": 0.7,    # 温度，控制随机性 (0-2)
    "top_p": 1.0,          # 核采样参数 (0-1)
    "stream": False,       # 是否流式输出
    "extra_body": {        # 推理模型专用
        "chat_template_kwargs": {
            "enable_thinking": True
        }
    }
}
```

### 推理模型输出格式

```python
# 非流式
message = response.choices[0].message
content = message.content                      # 最终回复
reasoning = message.reasoning_content         # 推理过程

# 流式
for chunk in response:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content)                  # 最终回复
    if delta.reasoning_content:
        print(delta.reasoning_content)       # 推理过程
```

## 测试建议

1. **先检查模型列表**：
```bash
python -c "from src.nvidia_client import NvidiaClient; c = NvidiaClient(api_key='你的KEY'); [print(m.id) for m in c.list_models()]"
```

2. **从小请求开始**：`max_tokens=50`，`"回复 OK"`
3. **注意超时**：推理模型可能需要 60-120 秒
4. **记录结果**：将测试结果更新到 `docs/NVIDIA_免费模型测试记录.md`

## 已知问题

### SSL 连接问题

现象：`[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]`

解决：
- 确保 SSL 证书路径正确
- 或使用 `verify=False`（仅调试）

### 流式响应卡住

某些推理模型在推理完成后可能不会发送 `finish_reason`，需要客户端主动处理完成。

### GLM 5 模型无响应

`z-ai/glm5` 目前不可用，已在 `glm5.py` 中标注。

## 参考链接

- [NVIDIA NIM API 文档](https://docs.api.nvidia.com/nim/)
- [模型列表](https://build.nvidia.com/explore/discover)
- [项目测试记录](../docs/NVIDIA_免费模型测试记录.md)