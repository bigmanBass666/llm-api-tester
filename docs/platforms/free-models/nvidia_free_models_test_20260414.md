# NVIDIA 免费模型测试记录

**测试日期**: 2026-04-14（新增 Qwen 3.5 122B 测试）
**API Key**: `nvapi-REMOVED-FOR-SECURITY`
**测试环境**: Windows 11, Python 3.12, OpenAI SDK 2.31.0

---

## 一、问题背景

用户反映 minimax-m2.7 模型（2026-04-11 上线）在调用时超时，而其他模型正常。经过多轮测试和调试，最终确认了所有可用模型的正确调用方式。

---

## 二、可用模型列表

### ✅ 完全正常的模型（8个）

| 用户习惯名称 | NVIDIA API 名称 | 备注 |
|------------|-----------------|------|
| qwen3.5-122b-a10b | `qwen/qwen3.5-122b-a10b` | ✅ 新增，2.9秒快速响应 |
| qwen3-coder-480b-a35b-instruct | `qwen/qwen3-coder-480b-a35b-instruct` | |
| deepseek-v3.1-terminus | `deepseek-ai/deepseek-v3.1-terminus` | |
| llama-4-maverick-17b-128e-instruct | `meta/llama-4-maverick-17b-128e-instruct` | |
| kimi-k2-instruct-0905 | `moonshotai/kimi-k2-instruct-0905` | |
| minimax-m2.7 | `minimaxai/minimax-m2.7` | **之前超时，现已修复** |
| gemma-7b | `google/gemma-7b` | |
| phi-3-mini-128k-instruct | `microsoft/phi-3-mini-128k-instruct` | |

### ⚠️ 需要注意的模型（2个）

| 用户习惯名称 | NVIDIA API 名称 | 问题说明 |
|------------|-----------------|---------|
| step-3.5-flash | `stepfun-ai/step-3.5-flash` | 简单问题正常，复杂问题可能只输出 reasoning |
| glm4.7 | `z-ai/glm4.7` | 只输出 reasoning_content，需要特殊提示词格式 |

### ❌ 不可用模型（1个）

| 用户习惯名称 | NVIDIA API 名称 | 问题说明 |
|------------|-----------------|---------|
| glm5 | `z-ai/glm5` | **模型未部署/不响应** — 虽然在 `/v1/models` 列表中出现，但 chat completions 请求超时无响应 |

---

## 三、模型名称对照表

```
用户写法                              → NVIDIA API 名称
─────────────────────────────────────────────────────────────
qwen3.5-122b-a10b                     → qwen/qwen3.5-122b-a10b
step-3.5-flash                        → stepfun-ai/step-3.5-flash
qwen3-coder-480b-a35b-instruct        → qwen/qwen3-coder-480b-a35b-instruct
deepseek-v3.1-terminus                → deepseek-ai/deepseek-v3.1-terminus
llama-4-maverick-17b-128e-instruct    → meta/llama-4-maverick-17b-128e-instruct
kimi-k2-instruct-0905                 → moonshotai/kimi-k2-instruct-0905
glm4.7                                → z-ai/glm4.7
minimax-m2.7                          → minimaxai/minimax-m2.7
gemma-7b                              → google/gemma-7b
phi-3-mini-128k-instruct              → microsoft/phi-3-mini-128k-instruct
glm5                                  → z-ai/glm5  (不可用)
```

---

## 四、通用测试代码

```python
import os
import httpx
from openai import OpenAI

from src.ssl_config import setup_ssl_certificates
setup_ssl_certificates()

# 创建客户端
with httpx.Client(verify=True, timeout=15) as client:
    openai_client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="nvapi-REMOVED-FOR-SECURITY",
        http_client=client
    )

    # 调用模型
    completion = openai_client.chat.completions.create(
        model="minimaxai/minimax-m2.7",  # 替换为任意模型名
        messages=[{"role": "user", "content": "你好"}],
        max_tokens=100,
        temperature=0.7
    )

    print(completion.choices[0].message.content)
```

---

## 五、获取完整模型列表

可以通过以下代码获取 NVIDIA API 所有可用模型：

```python
models = openai_client.models.list()
for model in sorted(models.data, key=lambda x: x.id):
    print(model.id)
```

---

## 六、问题记录

### 1. minimax-m2.7 超时问题（已解决）
- **日期**: 2026-04-12
- **现象**: API 调用超时，服务器接收请求但不响应
- **原因**: 模型刚上线，部署不完善
- **解决**: 2026-04-13 重测已恢复正常

### 2. 部分模型名称不匹配
- 多个模型的 NVIDIA API 名称与用户习惯写法不同
- 通过 `models.list()` 获取完整列表后一一验证

### 3. 推理模型（GLM、Step）输出特殊
- `z-ai/glm4.7` 和 `stepfun-ai/step-3.5-flash` 是推理模型
- 回复放在 `reasoning_content` 而非 `content`
- 需要研究特殊提示词格式

---

## 七、文件结构

```
D:\Test\api_key_test\
├── minimax-m2.7\
│   ├── NVIDIA_API_问题报告.md
│   └── NVIDIA_API_问题报告.md (隐藏API Key版)
├── qwen3-coder-480b\
│   ├── NVIDIA_API_测试报告.md
│   ├── test_nvidia.py
│   ├── test_nvidia_fixed.py
│   └── test_nvidia_skip_ssl.py
├── test_all_free_models.py      # 批量测试脚本
├── test_model_variants.py       # 模型名称变体测试
├── NVIDIA_免费模型测试记录.md    # 本文件
└── forum_post_content.md        # 论坛发帖模板
```

---

## 八、参考链接

- NVIDIA API 文档: https://docs.api.nvidia.com/
- NVIDIA NIM 论坛: https://forums.developer.nvidia.com/c/ai-data-science/nim
- build.nvidia.com: https://build.nvidia.com/

---

**最后更新**: 2026-04-14

---

## 九、GLM5 测试详情（2026-04-14）

### 测试结果：❌ 模型不响应

**模型 ID**: `z-ai/glm5`（在 `/v1/models` 列表中存在，`owned_by: z-ai`）

**测试方法**:
1. 调用 `POST /v1/chat/completions`，`model: "z-ai/glm5"`，消息 `{"role":"user","content":"OK"}`
2. 超时设置 120s，curl 60s
3. 对照组：`z-ai/glm4.7` 完全正常（TTFT 433ms，返回 `reasoning_content`）

**现象**:
- HTTP 请求发送成功（`models.list()` 返回模型信息）
- 服务器接收请求后不响应，TCP 连接超时
- 禁用 SSL 验证、切换流式/非流式均失败
- 错误类型：`httpx.ReadError`（SSL DECRYPTION_FAILED_OR_BAD_RECORD_MAC）、`APITimeoutError`、`APIConnectionError`

**结论**: `z-ai/glm5` 虽在 NVIDIA NIM 模型注册表中出现，但实际后端服务未部署或未就绪，无法处理 chat 请求。

**建议**: 在 NVIDIA NIM 官网 https://build.nvidia.com/z-ai/glm5 查看模型状态，或向 NVIDIA 反馈。