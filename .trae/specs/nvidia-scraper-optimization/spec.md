# NVIDIA 爬虫优化实施 Spec

## Why
基于页面结构深度探索的发现（见 nvidia-page-structure-exploration），当前爬虫存在三个核心问题导致只能获取 24 个模型：
1. **错误假设**: 使用无限滚动策略，但实际是传统分页系统
2. **选择器不精确**: 使用宽泛的 CSS 选择器导致误匹配
3. **URL 缺少参数**: 未使用 `?pageSize=96` 优化参数

**目标**: 将爬取覆盖率从 12.6% (24/191) 提升至 ~100% (191/191)

## What Changes
- **修改 URL 构建**: 添加 `&pageSize=96` 参数，单页获取 96 个模型
- **替换滚动逻辑**: 将 `_scroll_for_more()` 改为 `_go_to_next_page()` 分页遍历
- **更新选择器**: 使用 `[data-testid="nv-card-root"]` 精确定位模型卡片
- **增强数据提取**: 利用新发现的 DOM 结构提取更多字段（发布商、标签、描述）
- **验证优化效果**: 确保能成功获取全部 191 个模型

## Impact
- Affected specs: nvidia-page-structure-exploration (依赖其发现)
- Affected code:
  - `crawler/scraper.py` - 核心修改（URL、选择器、分页逻辑、数据提取）
  - `crawler/main.py` - 可能需要调整参数传递
  - `crawler/models.py` - 可能需要扩展 ModelInfo 数据结构

## ADDED Requirements

### Requirement: URL 参数优化
系统 SHALL 在访问 NVIDIA 模型列表时使用优化的 URL 参数以最大化单次请求的数据量。

#### Scenario: 使用 pageSize=96 参数
- **WHEN** 构建爬取 URL 时
- **THEN** 应自动添加 `&pageSize=96` 参数到 URL
- **AND** 对于热度排序: `https://build.nvidia.com/models?orderBy=weightPopular%3ADESC&pageSize=96`
- **AND** 对于最新排序: `https://build.nvidia.com/models?pageSize=96`
- **AND** 单次请求应返回约 96 个模型卡片（而非默认的 24 个）

#### Scenario: 保持向后兼容
- **WHEN** 用户未指定 pageSize 时
- **THEN** 默认使用 96（而非原来的无参数）
- **AND** 可通过命令行参数覆盖（如需）

### Requirement: 分页遍历机制
系统 SHALL 实现正确的分页遍历逻辑以获取所有模型。

#### Scenario: 遍历所有页面
- **WHEN** 当前页面模型数量不足时
- **THEN** 应点击"下一页"按钮 (`button[aria-label="Go to next page"]`)
- **AND** 等待新页面加载完成（2-3秒）
- **AND** 提取新页面的模型并去重
- **AND** 重复直到下一页按钮变为 disabled 或达到目标数量

#### Scenario: 智能终止条件
- **WHEN** 连续翻页后仍无新模型时
- **THEN** 应停止遍历并记录警告日志
- **AND** 最大翻页次数限制为 10 次（防止无限循环）

### Requirement: 精确选择器更新
系统 SHALL 使用 Playwright 探索发现的精确选择器定位元素。

#### Scenario: 模型卡片选择器
- **WHEN** 提取模型卡片时
- **THEN** 应使用 `[data-testid="nv-card-root"]` 选择器
- **AND** 不再使用宽泛的选择器（如 `div[class*="card"]`）
- **AND** 选择结果应准确匹配模型卡片（无遗漏或误匹配）

#### Scenario: 分页控件选择器
- **WHEN** 操作分页控件时
- **THEN** 应使用以下精确选择器:
  - 分页容器: `[data-testid="nv-pagination-root"]`
  - 下一页: `button[aria-label="Go to next page"]`
  - 页码输入: `input[data-testid="nv-text-input-element"]`

### Requirement: 增强数据提取
系统 SHALL 从模型卡片中提取完整的元数据信息。

#### Scenario: 提取发布商信息
- **WHEN** 解析每个模型卡片时
- **THEN** 应提取发布商名称（如 NVIDIA, Moonshotai, Meta）
- **AND** 存储到 ModelInfo.vendor 字段

#### Scenario: 提取标签信息
- **WHEN** 解析每个模型卡片时
- **THEN** 应提取所有标签徽章（Downloadable, Free Endpoint, Deprecation in 7d 等）
- **AND** 存储到 ModelInfo.tags 列表
- **AND** 设置 is_downloadable / is_free_endpoint 布尔标志

#### Scenario: 提取完整模型 ID
- **WHEN** 解析模型名称链接时
- **THEN** 应从 href 属性提取完整路径（如 `/nvidia/nemotron-3-super-120b-a12b`）
- **AND** 组合为标准格式 `{vendor}/{model-name}`

### Requirement: 性能验证
系统优化后应能达到预期的性能指标。

#### Scenario: 获取全部模型
- **WHEN** 执行 `python crawler/main.py -n 200 --scrape-only --sort-by popular`
- **THEN** 应成功返回至少 150 个不重复模型（目标 191 个）
- **AND** 不应出现重复模型或提前终止的情况

#### Scenario: 执行效率
- **WHEN** 完整爬取 191 个模型时
- **THEN** 总耗时应在 60 秒以内（2-3 次请求 + 解析时间）
- **AND** 不应触发 API 限流或被封禁

## MODIFIED Requirements

### Requirement: 爬虫主流程 (scraper.py)
原有的 `scrape_models()` 方法需要重构：

**修改点**:
1. URL 构建逻辑：添加 `pageSize=96` 参数
2. 主循环条件：从"滚动检测"改为"分页遍历"
3. 终止条件：从"连续无新内容"改为"下一页不可用"
4. 模型提取：调用增强版的 `_extract_models()`

### Requirement: 模型提取逻辑 (_extract_models)
原有的 `_extract_models()` 方法需要重构：

**修改点**:
1. 卡片选择器：改为 `[data-testid="nv-card-root"]`
2. 数据提取：利用新 DOM 结构提取 vendor/tags/description
3. 去重逻辑：保持不变但优化性能

## REMOVED Requirements

### Requirement: 无限滚动逻辑 (_scroll_for_more)
**原因**: 已证实 NVIDIA 使用传统分页系统，滚动策略完全无效
**迁移**: 替换为 `_go_to_next_page()` 分页方法

---

## Technical Notes

### 关键发现回顾（来自 PAGE_STRUCTURE_ANALYSIS.md）
1. **总模型数**: 191 个
2. **默认配置**: 24 models/page × 8 pages
3. **优化配置**: **96 models/page × 2 pages** ⭐
4. **分页组件**: nv-pagination (NVIDIA 自定义)
5. **模型卡片**: [data-testid="nv-card-root"]

### 推荐实现策略
采用 **策略 A: URL 参数优化**（详见 PAGE_STRUCTURE_ANALYSIS.md 第 6 章）:
- 最简单：只需改 URL
- 最可靠：不依赖 JS 操作 DOM
- 最高效：2 次请求覆盖全部

### 代码改动范围估计
- `crawler/scraper.py`: 约 80-100 行修改
  - `scrape_models()`: 重构主循环（~30 行）
  - `_extract_models()`: 更新选择器和提取逻辑（~40 行）
  - 新增 `_go_to_next_page()`: 替代原 `_scroll_for_more()`（~15 行）
  - 删除或注释 `_scroll_for_more()`, `_fallback_extract()` 等无用方法
- `crawler/models.py`: 可能添加 vendor 字段（~5 行）
- `crawler/main.py`: 可能微调参数传递（~5 行）

### 风险评估
- **低风险**: 改动集中在 scraper.py，不影响其他模块
- **注意事项**: 
  - 保留旧代码作为备份（注释掉而非删除）
  - 先用小数量测试（-n 10）验证后再跑全量
  - 监控日志确认无异常
