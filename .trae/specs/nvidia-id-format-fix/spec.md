# NVIDIA 模型 ID 格式修复 Spec

## Why
通过 Playwright 探索发现 **404 错误的根本原因**：NVIDIA 网页 URL 使用下划线 `_`（如 `deepseek-v3_2`），但实际 API 调用需要点号 `.`（如 `deepseek-v3.2`）。

这导致 **20+ 个模型**返回 404 错误，成功率只有 52%。修复后预期提升至 >80%。

## What Changes
- 在爬虫提取模型 ID 后，自动将下划线 `_` 转换为点号 `.`
- 添加 `fix_model_id()` 工具函数
- 在 `_extract_models()` 和测试器中应用此转换

### 影响范围
预计可修复的模型：
- DeepSeek: `deepseek-v3_2` → `deepseek-v3.2`, `deepseek-v3_1-terminus` → `deepseek-v3.1-terminus`
- Meta Llama: `llama-3_1-*` → `llama-3.1-*`, `llama-3_3-*` → `llama-3.3-*`
- Qwen: `qwen2_5-*` → `qwen2.5-*`
- 其他含下划线的模型

## Impact
- Affected code:
  - `crawler/scraper.py`: 提取逻辑中添加 ID 修复
  - `crawler/models.py`: 可能添加 fix 方法
  - `platforms/nvidia/tester.py`: 测试时也需使用正确 ID

## ADDED Requirements

### Requirement: ID 格式自动修复
系统 SHALL 在提取模型 ID 后自动将下划线转换为点号

#### Scenario: 提取后自动修复
- **WHEN** 爬虫从网页提取到模型 ID（如 `deepseek-v3_2`）
- **THEN** 自动转换为正确的 API ID（`deepseek-v3.2`）
- **AND** 存储修复后的 ID 到 ModelInfo

#### Scenario: 双重保障
- **WHEN** 测试器调用 API 时
- **THEN** 也对 model ID 进行同样的格式修复
- **AND** 确保即使爬虫漏修也能正常工作

## Implementation Notes

### 修复函数
```python
def fix_model_id(model_id: str) -> str:
    """将 NVIDIA 网页 ID 转换为 API 所需的 ID 格式
    
    NVIDIA 网页 URL 使用下划线 (deepseek-v3_2)，
    但实际 API 需要点号 (deepseek-v3.2)
    
    Args:
        model_id: 从网页提取的原始 ID
        
    Returns:
        修复后的 ID（下划线替换为点号）
    """
    return model_id.replace('_', '.')
```

### 应用位置
1. `_extract_models()` 中设置 `model_info.id = fix_model_id(raw_id)`
2. 测试器的 `test_single_model()` 中也应用一次（双重保障）

### 不需要修复的情况
- 已经是点号的 ID（无变化）
- Mistral、Stockmark 等 URL 本身就一致的模型
