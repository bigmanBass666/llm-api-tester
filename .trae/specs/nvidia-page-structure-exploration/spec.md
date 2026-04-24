# NVIDIA 页面结构深度探索 Spec

## Why
当前爬虫只能获取 24 个模型（单页限制），无法翻页导致测试覆盖不足。需要通过 Playwright MCP 直接探明 NVIDIA 网站的页面结构、分页机制和 DOM 组织方式，从根本上解决爬取限制问题。

## What Changes
- 使用 Playwright MCP 工具深度分析 NVIDIA 模型列表页面的 DOM 结构
- 识别分页机制（翻页按钮/无限滚动/加载更多按钮）
- 提取精确的 CSS 选择器用于模型卡片、分页控件等关键元素
- 编写详细的页面结构文档供后续爬虫优化使用

## Impact
- Affected specs: nvidia-batch-test-fix (后续优化依赖此探索结果)
- Affected code:
  - `crawler/scraper.py` - 将基于探索结果重构选择器和分页逻辑
  - 未来可能新增页面结构文档

## ADDED Requirements

### Requirement: 页面结构深度分析
系统 SHALL 能够通过浏览器自动化工具完整探明 NVIDIA 模型列表页面的 DOM 结构和组织方式。

#### Scenario: 成功访问并分析页面
- **WHEN** 使用 Playwright 访问 https://build.nvidia.com/models
- **THEN** 应能获取完整的页面快照（snapshot）
- **AND** 识别出所有关键的 DOM 元素（模型卡片容器、分页控件等）

### Requirement: 分页机制识别
系统 SHALL 能够准确识别 NVIDIA 网站使用的分页或加载更多机制。

#### Scenario: 发现翻页机制
- **WHEN** 分析页面底部或滚动区域时
- **THEN** 应能识别出以下至少一种机制：
  - 传统分页按钮（Next/Previous/Page numbers）
  - "Load More" 或 "Show More" 按钮
  - 无限滚动触发器
  - API 端点动态加载

#### Scenario: 验证翻页功能
- **WHEN** 找到分页控件后
- **THEN** 应能点击或触发翻页操作
- **AND** 确认新页面加载了不同的模型列表

### Requirement: 选择器提取
系统 SHALL 为所有关键元素提供精确的 CSS 选择器或 XPath。

#### Scenario: 提取模型卡片选择器
- **WHEN** 分析模型列表区域时
- **THEN** 应提取出：
  - 模型卡片的容器选择器
  - 单个模型卡片的精确选择器
  - 模型名称、标签、描述等子元素的选择器

#### Scenario: 提取分页控件选择器
- **WHEN** 分析分页区域时
- **THEN** 应提取出：
  - 分页容器的选择器
  - 下一页/上一页按钮的选择器
  - 页码按钮的选择器（如有）

### Requirement: 结构文档生成
系统 SHALL 生成详细的页面结构文档，包含 DOM 层级关系和交互说明。

#### Scenario: 输出完整分析报告
- **WHEN** 完成页面探索后
- **THEN** 应生成包含以下内容的文档：
  - 页面整体布局说明
  - 关键区域的 DOM 树结构
  - 所有可交互元素的位置和用途
  - 推荐的爬虫策略（基于实际发现的机制）
