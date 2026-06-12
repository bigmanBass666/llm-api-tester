# 🏛️ 设计原则审查报告（Post Phase 5）

> 审查日期: 2026-06-01  
> 审查范围: Phase 5 完成后的全量代码  
> 原则框架: SRP / DRY / KISS / OCP / DIP / ISP / LoD / YAGNI

---

## 📊 总览

| 原则 | 状态 | 严重度 |
|------|------|--------|
| SRP | ⚠️ 部分违反 | 🟡 中 |
| DRY | ⚠️ 部分违反 | 🟡 中 |
| KISS | ⚠️ 部分违反 | 🟡 中 |
| OCP | ✅ 满足 | — |
| DIP | ✅ 满足 | — |
| ISP | ✅ 满足 | — |
| LoD | ⚠️ 部分违反 | 🟢 低 |
| YAGNI | ⚠️ 部分违反 | 🟡 中 |

---

## 🔴 严重（运行时 Bug）

### 1. report/generator.py — TAG_ICONS 类属性缺失

**文件**: `report/generator.py:183`

**问题**: `MarkdownFormatter._format_tags()` 引用了 `self.TAG_ICONS`，但该常量在类中从未定义，运行时会报 `AttributeError`。

**修复**: 添加缺失的 `TAG_ICONS` 类属性或模块级常量。

---

## 🟡 中等（设计缺陷）

### 2. crawler/models.py — ModelInfo 别名 + 孤立的推理函数

**文件**: `crawler/models.py:12`

**违反**: DRY、SRP

**问题**:
- `ModelInfo = SrcModelInfo` 是逐字别名，注释自己标注了"Phase 5 后删除"
- `is_reasoning_model()` / `get_reasoning_effort()` 是本地的函数，但推理模型分类本应是平台层职责
- `ModelStore` 只被 `crawler/tester.py` 自己使用

**修复方向**:
- 删掉 ModelInfo 别名，直接 import `src.models.ModelInfo`
- 将 `is_reasoning_model`/`get_reasoning_effort` 迁移到 `src/model_classifier.py`
- 考虑将 `ModelStore` 并入 `src/` 或废弃

### 3. ConfigLoader / PlatformConfigLoader — 双层 YAML 加载

**文件**: `src/config_loader.py` vs `src/platform_config.py`

**违反**: DRY、SRP

**问题**:
- 两个类都加载 `configs/platforms.yaml`，各有独立解析逻辑
- `ConfigLoader.get_api_key()` 委托给 `registry.get_api_key()`（环境变量）
- `PlatformConfig` 也存了 `api_key_env`，有第三条路径
- 三处知道怎么获取 API key，只有两处实际在用

**修复方向**: 统一配置加载路径，`ConfigLoader` 完全委托给 `PlatformConfigLoader` 或合并

### 4. crawler/scraper.py — 过时的兼容层

**文件**: `crawler/scraper.py:1-143`

**违反**: KISS、YAGNI

**问题**:
- 143 行中约 50 行是注释和文档字符串
- `NvidiaScraper.scrape_models()` / `init_browser()` 向后兼容包装——没有代码调用它们
- `__main__` 里的 `test()` 函数已过时

**修复方向**: 精简为纯转发（只保留 re-export），或直接删除

### 5. batch.py — 新/旧路径双轨制

**文件**: `scripts/commands/batch.py:161-209`

**违反**: KISS、SRP

**问题**:
- `legacy_mode` 分支走 `crawler.tester.test_top_models`
- 非 legacy 分支走平台 `tester.batch_test`
- NVIDIA 标记了 `legacy_mode: true`，永远走旧路径，新功能只在新路径

**修复方向**: 迁移 legacy 平台到新路径，或明确标注 deprecated

---

## 🟢 低（代码质量改进）

### 6. TestResult.to_dict() — 重复条件表达式

**文件**: `src/models.py:147-167`

**违反**: KISS

**问题**: 8 行几乎相同的 `s.xxx if s else yyy` 模式

**修复**: 用 `ScrapedMetadata()` 默认值简化：
```python
s = self.scraped or ScrapedMetadata()
# 然后用 s.call_volume, s.published_at 等
```

### 7. report/generator.py — Markdown 模板硬编码

**文件**: `report/generator.py:41-176`

**违反**: KISS

**问题**:
- tags 说明表格、标题格式、表头全是中文字符串写在代码中
- 6 个格式化方法（`_format_endpoint_type`, `_format_deprecation`, `_format_call_volume`, `_format_published_at`, `_format_tags`）每个只被调用一次

**修复**: 提取为模块级常量或 Jinja2 模板；内联一次性格式化方法

### 8. platform_registry.py — API key 获取逻辑不一致

**文件**: `platform_registry.py:186-197`

**违反**: DRY

**问题**: `registry.get_api_key()` 从环境变量读，`PlatformConfig` 也存了 `api_key_env`，`ConfigLoader` 也有一套——三处知道，两处使用

---

## 💡 优先修复排序

| # | 优先级 | 问题 | 预期收益 |
|---|--------|------|---------|
| 1 | 🔴 高 | report/generator.py TAG_ICONS 缺失 — 运行时 crash | 修复报告功能 |
| 2 | 🟡 中 | crawler/models.py 别名 + 孤立逻辑 | 消除重复定义，单源分类逻辑 |
| 3 | 🟡 中 | ConfigLoader / PlatformConfigLoader 双层加载 | 减少维护面 |
| 4 | 🟡 中 | crawler/scraper.py 兼容层冗余 | 减少 143 行死代码 |
| 5 | 🟢 低 | batch.py legacy 路径双轨制 | 减少复杂度 |
| 6 | 🟢 低 | TestResult.to_dict() 重复条件表达式 | 简化 8 行样板 |
| 7 | 🟢 低 | report/generator.py 模板硬编码 | 可维护性 |
| 8 | 🟢 低 | platform_registry.py API key 路径不一致 | 统一入口 |

---

## ✅ 本次重构做得好的地方

1. **ScrapedMetadata 分离**: 8 个爬虫字段从 ModelInfo/TestResult 干净分离，语义清晰
2. **TestResult.from_model_info()**: 替代四处分散的 `_model_to_result_kwargs`，统一转换逻辑
3. **base_tester 精简**: `_model_to_result_kwargs` 从 13 个字段缩减到 7 个
4. **@register_platform 装饰器**: 声明式设计，OCP 做得好
5. **全平台构造统一**: 所有 client 构造 ModelInfo 都统一到 `scraped=ScrapedMetadata(...)`
6. **测试覆盖**: 144+ 单元测试 + 集成测试全过
