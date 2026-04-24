# Tasks

## 阶段一：Playwright 探索模型详情页
- [x] Task 1: 访问 DeepSeek 模型详情页 ✅
  - [x] SubTask 1.1: 访问 https://build.nvidia.com/deepseek-ai/deepseek-v3_2
  - [x] SubTask 1.2: 提取 API 调用代码示例（Python/cURL）
  - [x] SubTask 1.3: 记录 model ID、endpoint、请求格式
  
- [x] Task 2: 访问 Meta Llama 模型详情页 ✅
  - [x] SubTask 2.1: 访问 https://build.nvidia.com/meta/llama-3_1-8b-instruct
  - [x] SubTask 2.2: 提取 API 调用信息
  - [x] SubTask 2.3: 对比网页 ID 与实际 API ID

- [x] Task 3: 访问成功模型作为对照 ✅
  - [x] SubTask 3.1: 访问 https://build.nvidia.com/mistralai/mistral-nemotron
  - [x] SubTask 3.2: 提取 API 调用信息
  - [x] SubTask 3.3: 对比成功与失败模型的差异

## 阶段二：分析总结
- [x] Task 4: 对比分析 ID 差异 ✅
  - [x] SubTask 4.1: 整理所有模型的 ID 格式
  - [x] SubTask 4.2: 找出 ID 变化规律（下划线 vs 点号）
  - [x] SubTask 4.3: 分析 404 根本原因

- [x] Task 5: 输出探索报告 ✅
  - [x] SubTask 5.1: 总结发现的问题
  - [x] SubTask 5.2: 提出修复建议

# Notes
- ⭐ **核心问题**: 为什么 DeepSeek 等模型返回 404？
- 🔍 **关键假设**: 网页显示的 ID 可能不是实际 API 需要的 ID → **已验证！**
- 📊 **对比方法**: 成功模型 vs 失败模型，找出差异 → **已完成**

# 探索结果总结

## 🔴 根本原因：ID 格式不一致！

### 问题规律
| 模型 | 网页 URL | 页面标题 | **正确 API ID** | 我们用的 ID |
|------|---------|---------|----------------|------------|
| DeepSeek v3.2 | `deepseek-v3_2` ❌ | `deepseek-v3.2` ✅ | `deepseek-ai/deepseek-v3.2` ✅ | `deepseek-ai/deepseek-v3_2` ❌ |
| Llama 3.1 8B | `llama-3_1-8b-instruct` ❌ | `llama-3.1-8b-instruct` ✅ | `meta/llama-3.1-8b-instruct` ✅ | `meta/llama-3_1-8b-instruct` ❌ |
| Mistral Nemotron | `mistral-nemotron` ✅ | `mistral-nemotron` ✅ | `mistralai/mistral-nemotron` ✅ | `mistralai/mistral-nemotron` ✅ |

### 规律总结
- **失败模型**: URL 用**下划线 `_`**，但 API 需要**点号 `.`**
- **成功模型**: URL 和 API ID 完全一致（无下划线/点号差异）

### 修复方案
在爬虫提取模型 ID 后，需要将**下划线转换为点号**：
```python
# 修复函数
def fix_model_id(model_id: str) -> str:
    return model_id.replace('_', '.')
```

### 影响范围
预计可修复 **20+ 个模型**的 404 错误！
