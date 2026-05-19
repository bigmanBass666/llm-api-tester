# NVIDIA NIM API 参考文档

## 重要发现（2026-05-19）

### 1. 图像生成 API 端点

**自托管 NIM 容器**（localhost:8000）：
- 原生端点：`POST /v1/infer`
- OpenAI 兼容：`POST /v1/images/generations`
- 模型：flux.1-dev, flux.1-schnell, flux.1-kontext-dev, flux.2-klein-4b, stable-diffusion-3.5-large, qwen-image, qwen-image-edit

**云端 API**（integrate.api.nvidia.com）：
- 端点：`POST https://ai.api.nvidia.com/v1/genai/{model}`
- 仅 `flux.2-klein-4b` 可用（旧版 flux 全部下线）

### 2. 视频生成模型

**全部不可用**（云端 API 404）：
- cosmos-transfer2_5-2b, cosmos-transfer1-7b, cosmos-predict1-5b 等
- 仅支持自托管 NIM 部署

### 3. 聊天模型 API

- 端点：`POST /v1/chat/completions`
- API 列出 125 个模型，实际可用 51 个（41%）
- `created` 字段是占位符（所有模型相同值 735790403）

### 4. 模型分类

| 类型 | 端点 | 云端可用 |
|------|------|---------|
| 聊天/推理 | /v1/chat/completions | 51 个模型 |
| 图像生成 | /v1/genai/{model} | 仅 flux.2-klein-4b |
| 视频生成 | /v1/infer (自托管) | 无 |
| 嵌入 | /v1/embeddings | 部分可用 |
| 语音 | /v1/audio/* | 部分可用 |

## 图像生成调用示例

### 云端 API（flux.2-klein-4b）
```python
import httpx, base64

url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"
headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
payload = {
    "prompt": "a cute frog sitting on a lily pad",
    "width": 1024,
    "height": 1024,
    "seed": 42
}

response = httpx.post(url, headers=headers, json=payload, timeout=120)
img_bytes = base64.b64decode(response.json()['artifacts'][0]['base64'])
```

### 自托管 NIM（OpenAI 兼容）
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
response = client.images.generate(
    model="black-forest-labs/flux.2-klein-4b",
    prompt="a simple coffee shop interior",
    n=1,
    response_format="b64_json",
)
```

## 文档来源

- Visual GenAI 概述：https://docs.nvidia.com/nim/visual-genai/latest/overview.html
- OpenAI 兼容图像 API：https://docs.nvidia.com/nim/visual-genai/latest/api/openai-image-generation.html
- FLUX.2-klein API 参考：https://docs.nvidia.com/nim/visual-genai/1.4.0/api/flux.2-klein.html
