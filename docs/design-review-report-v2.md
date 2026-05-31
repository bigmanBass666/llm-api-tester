# 🏛️ 设计原则审查报告（Post Phase 5 — 第二轮）

> 审查日期: 2026-06-01
> 审查范围: Phase 5 + 第一轮修复完成后的全量代码
> 原则框架: SRP / DRY / KISS / OCP / DIP / ISP / LoD / YAGNI
> 对比基线: `docs/design-review-report.md`（第一轮，8 条发现）

---

## 📊 总览

| 原则 | 状态 | 严重度 | 变化 |
|------|------|--------|------|
| SRP | ✅ 基本满足 | — | ⬆️ 改善 |
| DRY | ⚠️ 部分违反 | 🟡 中 | ⬆️ 改善 |
| KISS | ⚠️ 部分违反 | 🟡 中 | → 持平 |
| OCP | ✅ 满足 | — | → 持平 |
| DIP | ✅ 满足 | — | → 持平 |
| ISP | ✅ 满足 | — | → 持平 |
| LoD | ⚠️ 部分违反 | 🟢 低 | → 持平 |
| YAGNI | ⚠️ 部分违反 | 🟡 中 | → 持平 |

**第一轮 8 条发现全部修复**，本轮发现 5 个新问题（均为中低优先级）。

---

## ✅ 第一轮修复验证

| # | 问题 | 状态 | 验证 |
|---|------|------|------|
| 1 | TAG_ICONS 缺失运行时 bug | ✅ 已修复 | `report/generator.py:15-21` 模块级常量已定义 |
| 2 | crawler/models.py 别名 | ✅ 已修复 | 推理函数已迁至 `src/model_classifier.py` |
| 3 | ConfigLoader 双层 YAML | ✅ 已修复 | `config_loader.py` 完全委托给 `PlatformConfigLoader` |
| 4 | crawler/scraper.py 143 行兼容层 | ✅ 已修复 | 精简到 30 行纯转发 |
| 5 | batch.py legacy 路径 | ✅ 已标注 | `DeprecationWarning` 已添加 |
| 6 | TestResult.to_dict() 重复表达式 | ✅ 已简化 | `s = self.scraped or ScrapedMetadata()` |
| 7 | report/generator.py 模板硬编码 | ✅ 已提取 | `TAG_ICONS` / `TAG_LEGEND` 模块级常量 |
| 8 | API key 路径不一致 | ✅ 已统一 | `get_api_key()` 统一走 `RegistryEntry.api_key_env` |

---

## 🔍 第二轮新发现

### 🟡 中等（设计缺陷）

#### N1. NvidiaClient 装饰器注册模式 — 类名覆盖陷阱

**文件**: `platforms/nvidia/client.py:241-249`, `platforms/zhipu/client.py:18-26`

**违反**: KISS, SRP

**问题**: `@register_platform(...)` 装饰器返回一个新类，覆盖了原始类名：
```python
class NvidiaClient(OpenAICompatibleClient):
    ...
NvidiaClient = register_platform(...)(NvidiaClient)  # 类名被覆盖
```
装饰器内部执行 `cls.platform_name = name` 等副作用，然后返回修改后的类。这导致：
1. `NvidiaClient` 的 `type` 不再是原始类（装饰器返回的是同一个对象，但语义上容易混淆）
2. 如果装饰器返回不同对象，`isinstance` 检查会失败
3. 与 `src/platform_registry.py:234` 的 `registry.register(config)` 耦合 — 装饰器既修改类又注册，做了两件事

**对比**: `KimiClient` 用了不同的模式 — 定义 `KimiClientWithConfig` 然后 `KimiClient = register_platform(...)(KimiClientWithConfig)`，原始类名保留。

**修复方向**: 统一注册模式。推荐 Kimi 的方式（保留原始类名），或改为显式调用 `registry.register()` 而非装饰器。

#### N2. NvidiaTester — model.id 临时替换的副作用

**文件**: `platforms/nvidia/tester.py:17-24`

**违反**: SRP, LoD

**问题**:
```python
async def test_single(self, model, timeout=60):
    api_model_id = model.id.replace('_', '.') if '_' in model.id else model.id
    original_id = model.id
    model.id = api_model_id          # 修改了入参对象
    result = await super().test_single(model, timeout)
    model.id = original_id           # 恢复
    result.model_id = original_id    # 修正结果
    return result
```
- 修改了入参 `model.id`（副作用），测试完再恢复 — 非线程安全，且违反"不修改入参"原则
- `result.model_id` 被手动覆盖，说明 `super().test_single()` 返回的 `model_id` 是错误的 — 应该在调用前就传入正确的 ID

**修复方向**: 将 ID 转换逻辑提取到 `NvidiaClient` 层（`fix_model_id`），tester 只接收已转换的 ID。或在 `test_single` 内用局部变量而非修改 `model.id`。

#### N3. KimiClient — 双路径模型列表加载

**文件**: `platforms/kimi/client.py:18-51`

**违反**: SRP, DRY

**问题**: `KimiClientWithConfig.list_models()` 有三条获取路径：
1. API 返回多个模型 → 直接用
2. API 返回 ≤1 个 → 从 `platforms.yaml` 读取
3. YAML 也失败 → 回退到 API 结果

路径 2 硬编码了 YAML 路径解析逻辑（`config.get('platforms', {}).get('kimi', {}).get('models', {}).get('free', [])`），与 `PlatformConfigLoader` 功能重复。且 `ZhipuScraper` 已经用 `PlatformConfigLoader.get_known_models()` 实现了同样的功能。

**修复方向**: 统一用 `PlatformConfigLoader` 获取配置模型列表，消除 Kimi 客户端中的裸 YAML 解析。

---

### 🟢 低（代码质量改进）

#### N4. NvidiaScraper._extract_models — 过长函数

**文件**: `platforms/nvidia/scraper.py:179-366`（187 行）

**违反**: SRP, KISS

**问题**: `_extract_models` 方法 187 行，内联了所有卡片解析逻辑：
- 模型 ID 提取（链接解析）
- 名称提取
- Vendor 提取
- 标签/徽章解析
- Category/Description 提取
- 调用量/发布时间提取（aria-label 解析）
- 端点类型判断
- 弃用信息正则匹配
- ModelInfo 构造

每个卡片的解析是一个独立关注点，全部堆在一个方法里。

**修复方向**: 拆分为 `_parse_card_id(card)`、`_parse_card_tags(card)`、`_parse_card_metadata(card)` 等辅助方法。每个方法只负责一个字段。

#### N5. OpenAICompatibleClient — 三个客户端类功能重叠

**文件**: `platforms/common/openai_compatible_client.py:1-206`

**违反**: DRY, ISP

**问题**:
- `OpenAICompatibleClient` — OpenAI 协议
- `AnthropicCompatibleClient` — Anthropic 协议
- `MiniMaxClient` — 继承 `OpenAICompatibleClient`，无额外代码（空类）

`MiniMaxClient` 是纯空类，仅用于 `platform_name` 标识。`AnthropicCompatibleClient` 与 `OpenAICompatibleClient` 有大量重复结构（`list_models`、`test_connection`、`close` 模式完全相同），但协议差异导致无法直接共享。

当前设计尚可接受（协议差异确实存在），但 `MiniMaxClient` 空类是 YAGNI 的体现 — 如果未来不需要特殊逻辑，直接用 `OpenAICompatibleClient` 即可。

**修复方向**: 暂不修改（当前复杂度可接受）。如果未来增加更多 OpenAI 兼容平台，考虑用工厂函数代替空类继承。

---

## 💡 优先修复排序

| # | 优先级 | 问题 | 预期收益 |
|---|--------|------|---------|
| N1 | 🟡 中 | 装饰器注册模式不一致 + 类名覆盖 | 统一注册模式，减少认知负担 |
| N2 | 🟡 中 | NvidiaTester model.id 副作用 | 消除可变状态，线程安全 |
| N3 | 🟡 中 | KimiClient 双路径模型列表 | 统一配置加载路径 |
| N4 | 🟢 低 | NvidiaScraper._extract_models 187 行 | 可读性 |
| N5 | 🟢 低 | MiniMaxClient 空类 | 暂不修改 |

---

## ✅ 本轮确认做得好的地方

1. **ScrapedMetadata 分离**: 第一轮已认可，本轮确认所有平台统一使用
2. **ModelClassifier 集中**: 推理函数从 crawler/models.py 迁到 src/model_classifier.py，分类逻辑单源化
3. **ConfigLoader 统一**: 双层 YAML 消除，PlatformConfigLoader 成为唯一配置源
4. **crawler/scraper.py 精简**: 143 行 → 30 行，纯转发层
5. **@register_platform 装饰器**: 声明式注册，OCP 做得好（尽管 N1 发现模式不一致）
6. **TestResult.from_model_info()**: 统一构造入口，消除分散的字段映射
7. **测试覆盖**: 158 passed，比第一轮 144 增加 14 个

---

## 📈 两轮对比

| 维度 | 第一轮 | 第二轮 | 变化 |
|------|--------|--------|------|
| 🔴 严重 | 1 | 0 | -1 ✅ |
| 🟡 中等 | 4 | 3 | -1 ✅ |
| 🟢 低 | 3 | 2 | -1 ✅ |
| 总计 | 8 | 5 | -3 ✅ |
| 测试通过 | 144 | 158 | +14 ✅ |
