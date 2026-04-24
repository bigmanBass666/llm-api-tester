# 非文字模型过滤方案 Spec

## Why
当前批量测试中约 38% 的模型是非文字模型（语音、图像、嵌入、蛋白质等），这些模型：
- 不支持标准文本输入 API（返回 400/404 错误）
- 浪费测试时间和 API 配额
- 降低有效测试覆盖率

需要设计一套机制在爬取阶段就过滤掉非文字模型，只保留可测试的**文本生成/聊天/推理模型**。

## What Changes
- 在 `_extract_models()` 中提取模型卡片的 **Category Tag**（分类标签）
- 新增 `ModelInfo.category` 字段存储模型类型
- 新增 `_is_text_model()` 方法判断是否为文字模型
- 新增配置项支持自定义过滤规则
- 在主循环中过滤非文字模型

### 核心发现（Playwright 探索结果）

**NVIDIA 网页模型卡片结构**：
```
┌─────────────────────────────────────┐
│ [Vendor Logo] Vendor Name           │
│ [Badge: Downloadable/Free]          │
│ model-name                          │
│ 模型描述文本...                     │
│ ★ category-tag ★  ← 关键字段!      │
│ [+N] 参数量    [XX.XM] 下载量       │
│ [Xmo] 发布时间                       │
└─────────────────────────────────────┘
```

**发现的 Category Tag 类型**：

| Tag | 类型 | 是否文字模型 |
|-----|------|-------------|
| text-generation | 文本生成 | ✅ |
| chat | 聊天 | ✅ |
| coding | 编码 | ✅ |
| reasoning | 推理 | ✅ |
| language generation | 语言生成 | ✅ |
| instruction following | 指令遵循 | ✅ |
| long-context | 长上下文 | ✅ |
| agentic | 代理 | ✅ |
| tool calling | 工具调用 | ✅ |
| moe | 混合专家 | ✅ (通常) |
| embedding / embeddings | 嵌入 | ❌ |
| text-to-embedding | 文本转嵌入 | ❌ |
| table extraction | 表格提取 | ❌ |
| text and table extraction | 文本表格提取 | ❌ |
| nvidia nim | NIM 特定 | ⚠️ 需进一步判断 |

## Impact
- Affected code:
  - `crawler/scraper.py`: 提取逻辑增强、新增过滤方法
  - `crawler/models.py`: ModelInfo 新增 category 字段
  - `crawler/main.py`: 可能新增命令行参数

## ADDED Requirements

### Requirement: Category Tag 提取
系统 SHALL 从模型卡片中提取 Category Tag 并存储到 ModelInfo.category

#### Scenario: 成功提取
- **WHEN** 爬虫解析模型卡片时
- **THEN** 提取描述下方的分类标签（如 "text-generation", "chat", "embedding"）
- **AND** 存储到 ModelInfo.category 字段

#### Scenario: 标签不存在
- **WHEN** 卡片没有 Category Tag
- **THEN** category 设为 None（不阻止后续处理）

### Requirement: 文字模型判断
系统 SHALL 提供可靠的文字模型识别机制

#### Scenario: 基于 Category Tag 判断
- **WHEN** 模型的 category 属于白名单
- **THEN** 判定为文字模型（is_text_model = True）

**白名单定义**：
```python
TEXT_MODEL_CATEGORIES = {
    'text-generation', 'chat', 'coding', 'reasoning',
    'language generation', 'instruction following',
    'long-context', 'agentic', 'tool calling', 'moe'
}
```

#### Scenario: 基于模型 ID 兜底判断
- **WHEN** Category 为空 或不在白名单/黑名单中
- **THEN** 使用模型 ID 黑名单辅助判断

**黑名单关键词**（匹配则判定为非文字）：
```python
NON_TEXT_KEYWORDS = [
    'whisper', 'flux', 'parakeet', 'stable-diffusion',
    'nemoretriever', 'esm2', 'nvclip', 'nemotron-parse',
    'riva-translate', 'magpie-tts', 'genmol', 'proteinmpnn',
    'rfdiffusion', 'shieldgemma', 'nemoguard', 'cosmos-'
]
```

### Requirement: 可配置过滤策略
系统 SHALL 支持通过参数控制是否启用过滤

#### Scenario: 启用过滤（默认）
- **WHEN** 用户运行 `python crawler/main.py --filter-text`
- **THEN** 只爬取和测试文字模型
- **AND** 日志显示过滤统计："过滤掉 X 个非文字模型"

#### Scenario: 禁用过滤
- **WHEN** 用户运行 `python crawler/main.py --no-filter`
- **THEN** 爬取所有模型（保持向后兼容）

## MODIFIED Requirements

### Requirement: _extract_models() 方法
修改后的方法 SHALL：
1. 提取 Category Tag（位于描述文本下方）
2. 设置 ModelInfo.category 字段
3. 调用 _is_text_model() 判断类型
4. 返回完整的模型信息（包含 category）

### Requirement: scrape_models() 主循环
修改后的主循环 SHALL：
1. 在去重后检查 is_text_model 标志
2. 如果启用了过滤且不是文字模型，记录日志并跳过
3. 统计被过滤的模型数量

## Implementation Notes

### Category Tag 提取位置
根据 Playwright 探索，Category Tag 位于卡片 innerText 的第 5 行（0-indexed）：
```python
lines = card.innerText.split('\n').filter(l => l.trim())
# lines[0] = Vendor
# lines[1] = Badge (Downloadable/Free)
# lines[2] = Model Name
# lines[3] = Description
# lines[4] = Category Tag ← 目标
# lines[5+] = Stats
```

### 选择器建议
如果上述行号不稳定，可以使用 CSS 类名定位（需进一步探索）。
