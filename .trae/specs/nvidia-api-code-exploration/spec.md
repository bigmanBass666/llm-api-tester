# NVIDIA 模型详情页 API 调用代码探索 Spec

## Why
批量测试中发现大量模型（特别是 DeepSeek）返回 404 错误，但 NVIDIA 网页上显示这些模型是可用的。需要深入分析：
1. **DeepSeek 模型为什么 404？** - 刚才还能用，现在不行了？
2. **API 调用代码是否变化？** - 详情页展示的调用示例是什么？
3. **模型 ID 格式是否改变？** - 网页 ID vs API ID 是否一致？

## What Changes
- 使用 Playwright MCP 访问 NVIDIA 模型详情页
- 提取页面上的 API 调用示例代码
- 对比网页显示的 ID 与实际 API 调用的 ID
- 分析 404 错误的根本原因

### 重点探索目标
1. **DeepSeek 模型**：deepseek-v3_2, deepseek-v3_1-terminus
2. **Meta Llama 模型**：llama-3_1-8b-instruct, llama-3.3-70b-instruct  
3. **成功调用的模型**：作为对照组（如 mistralai/mistral-nemotron）

## Impact
- Affected code: 无（纯探索任务）
- Affected specs: 可能影响后续 API 客户端修复

## ADDED Requirements

### Requirement: 模型详情页探索
系统 SHALL 使用 Playwright 访问 NVIDIA 模型详情页并提取 API 调用信息

#### Scenario: 访问 DeepSeek 模型详情页
- **WHEN** 访问 `https://build.nvidia.com/deepseek-ai/deepseek-v3_2`
- **THEN** 提取页面上的 API 调用代码示例
- **AND** 记录正确的 model ID、endpoint URL、请求格式

#### Scenario: 访问 Meta Llama 模型详情页
- **WHEN** 访问 `https://build.nvidia.com/meta/llama-3_1-8b-instruct`
- **THEN** 提取 API 调用信息并与当前使用的 ID 对比

#### Scenario: 访问成功模型作为对照
- **WHEN** 访问 `https://build.nvidia.com/mistralai/mistral-nemotron`
- **THEN** 提取 API 调用信息并对比差异

## Implementation Notes

### 需要提取的信息
1. **Model ID**: 页面显示的完整模型标识符
2. **Endpoint URL**: API 端点地址
3. **Request Body**: 请求体格式（特别是 model 字段）
4. **Headers**: 必需的认证头
5. **Code Examples**: Python/cURL 示例代码

### 关键假设验证
- 假设1: 网页 ID 与 API ID 不一致（如 deepseek-v3_2 vs deepseek-v3.2）
- 假设2: 某些模型需要特殊的 endpoint 或 header
- 假设3: 模型已下线但网页未更新
