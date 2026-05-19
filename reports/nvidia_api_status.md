# NVIDIA API 模型可用性报告

更新时间: 2026-05-19

## 聊天模型 (chat completions)

- API 列出: 125 个模型（去重后 119 个）
- 实际可用: 51 个 (41%)
- 不可用: 58 个 (404)
- 超时: 12 个
- 其他错误: 4 个

### 可用模型（部分）
- deepseek-ai/deepseek-v4-flash
- google/gemma-4-31b-it (14s 响应)
- meta/llama-3.3-70b-instruct
- meta/llama-4-maverick-17b-128e-instruct
- minimaxai/minimax-m2.7
- moonshotai/kimi-k2.6
- nvidia/nemotron-3-super-120b-a12b
- qwen/qwen3.5-397b-a17b
- stepfun-ai/step-3.5-flash

## 图像生成模型 (genai endpoint)

唯一可用: black-forest-labs/flux.2-klein-4b
- 端点: https://ai.api.nvidia.com/v1/genai/{model}
- 响应时间: ~8s (1024x1024)
- 所有旧版 flux 模型已下线 (404)

## API 问题

1. `created` 字段: 所有模型返回相同值 (735790403)，无意义
2. 重复条目: 6 个模型有重复 API 列表
3. 网站目录 vs API: 网站列出 357+ 模型，API 只有 125 个，实际可用 51 个
