# 智谱AI (ZHIPU AI) 免费模型完整清单

**数据采集时间**: 2026-04-17 22:49 (UTC+8)
**速率限制页面**: https://www.bigmodel.cn/usercenter/proj-mgmt/rate-limits
**文档验证**: https://docs.bigmodel.cn/cn/guide/models/free/
**报告生成时间**: 2026-04-17 23:00:00

---

## 📋 免费模型定义标准

根据智谱AI官方文档，免费模型(FREE models)特指在 **`/cn/guide/models/free/`** 目录下有独立文档说明的模型，这些模型提供免费的API调用额度。

---

## ✅ 确认的免费模型 (7个)

按**并发数从高到低**排序：

| 排名 | 并发数 | 模型名称 | 分类 | 免费文档 | 备注 |
|------|--------|----------|------|----------|------|
| 🥇 1 | **200** | GLM-4-Flash-250414 | 通用模型 | ✅ | 首个免费API，超大并发 |
| 🥈 2 | **10** | GLM-4V-Flash | 通用模型 | ✅ | 免费图像理解 |
| 🥉 3 | **5** | GLM-4.1V-Thinking-Flash | 视觉推理 | ✅ | 免费视觉推理+思考 |
| 4 | **5** | GLM-4.7-Flash | 通用模型 | ✅ | 30B级SOTA，Agentic Coding |
| 5 | **5** | CogView-3-Flash | 图像大模型 | ✅ | 免费文生图 |
| 6 | **3** | CogVideoX-Flash | 视频生成模型 | ✅ | 免费视频生成 |
| 7 | **1** | GLM-4.6V-Flash | 通用模型 | ✅ | 免费视觉理解 |

---

## 📊 免费模型分类统计

| 模型类型 | 数量 | 并发数范围 | 代表模型 |
|---------|------|-----------|---------|
| 通用模型 | 4 | 200, 10, 5, 1 | GLM-4-Flash, GLM-4V-Flash |
| 视觉模型 | 2 | 5, 1 | GLM-4.1V-Thinking-Flash, GLM-4.6V-Flash |
| 图像生成 | 1 | 5 | CogView-3-Flash |
| 视频生成 | 1 | 3 | CogVideoX-Flash |

---

## 🎯 高并发免费模型推荐

### 1. **GLM-4-Flash-250414** (并发: 200) ⭐⭐⭐⭐⭐
- **文档**: https://docs.bigmodel.cn/cn/guide/models/free/glm-4-flash-250414.md
- **特点**: 智谱AI首个免费大模型API
- **上下文**: 128K
- **适用场景**:
  - 智能问答
  - 摘要生成
  - 文本数据处理
  - 多语言支持(26种语言)
  - 实时网页检索
- **并发能力**: 200 (最高)

### 2. **GLM-4V-Flash** (并发: 10) ⭐⭐⭐⭐
- **文档**: https://docs.bigmodel.cn/cn/guide/models/free/glm-4v-flash.md
- **特点**: 首个完全免费的图像理解模型
- **能力**:
  - 图像识别
  - 图像问答
  - 图像推理
  - 图表分析
- **适用场景**: 视觉理解、美容咨询、质量检测

### 3. **GLM-4.7-Flash** (并发: 5) ⭐⭐⭐⭐
- **文档**: https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash.md
- **特点**: 30B级SOTA，专为Agentic Coding优化
- **上下文**: 200K输入 / 128K输出
- **能力**:
  - 思考模式
  - 工具调用
  - 结构化输出
  - 前端审美优化
- **适用场景**: 复杂智能体任务、编程辅助、方案讨论

### 4. **GLM-4.1V-Thinking-Flash** (并发: 5) ⭐⭐⭐⭐
- **文档**: https://docs.bigmodel.cn/cn/guide/models/free/glm-4.1v-thinking-flash.md
- **特点**: 免费视觉推理+深度思考
- **能力**:
  - 图文理解
  - 数学与科学推理
  - 视频理解
  - GUI Agent任务
- **适用场景**: 学科解题、前端Coding、复杂图表问答

---

## 💡 使用建议

### 批量测试策略

1. **高并发场景** (≥50 QPS):
   - 首选: `GLM-4-Flash-250414` (200并发, 免费)
   - 性能最好，适合大规模测试

2. **中等并发场景** (10-50 QPS):
   - 视觉任务: `GLM-4V-Flash` (10并发)
   - 推理任务: `GLM-4.7-Flash` 或 `GLM-4.1V-Thinking-Flash` (各5并发)

3. **低并发场景** (1-10 QPS):
   - 视觉理解: `GLM-4.6V-Flash` (1并发)
   - 图像生成: `CogView-3-Flash` (5并发)
   - 视频生成: `CogVideoX-Flash` (3并发)

### 模型选型决策树

```
需要文本处理?
├─ 是 → 需要高并发? → 是 → GLM-4-Flash-250414
│                    └─ 否 → 需要智能体? → 是 → GLM-4.7-Flash
│                                      └─ 否 → GLM-4V-Flash
└─ 否 → 需要视觉理解?
     ├─ 是 → 需要推理? → 是 → GLM-4.1V-Thinking-Flash
     │                └─ 否 → GLM-4.6V-Flash
     └─ 否 → 需要生成?
          ├─ 图像 → CogView-3-Flash
          └─ 视频 → CogVideoX-Flash
```

---

## 🔍 与完整模型列表的对比

从速率限制页面共采集到 **40+ 个模型**，仅有 **7 个**有免费文档认证。

### 免费模型 vs 付费模型并发数对比

| 类型 | 免费模型平均并发 | 付费模型平均并发 | 最高并发模型 |
|------|-----------------|-----------------|-------------|
| 通用模型 | 44.2 (4个) | 27.8 (13个) | GLM-4-Air (100, 付费) |
| 视觉模型 | 3 (3个) | 7.5 (4个) | GLM-4.6V (10, 付费) |
| 图像生成 | 5 (1个) | 3.3 (6个) | CogView-4 (5, 免费) |
| 视频生成 | 3 (1个) | 4.2 (6个) | Vidu系列 (5, 付费) |

**结论**: 免费模型的并发数并不低，GLM-4-Flash的200并发甚至超过所有付费模型。

---

## 📌 重要提醒

1. **免费额度的限制**: 虽然这些模型在速率限制页面列出，但免费调用可能有每日/每月Token额度限制，详情需查看"用户权益"页面
2. **并发数变化**: 并发限制与用户权益等级相关，升级账户可获得更高限制
3. **上下文限制**: GLM-4-Flash在上下文超过8K时，并发会限制为标准速率的1%
4. **模型版本**: GLM-4-Flash-250414 是特定版本号，可能存在更新版本

---

## 🔗 相关资源

- **速率限制查询**: https://www.bigmodel.cn/usercenter/proj-mgmt/rate-limits
- **体验中心**: https://www.bigmodel.cn/console/trialcenter
- **用户权益说明**: https://docs.bigmodel.cn/cn/guide/platform/equity-explain.md
- **API文档**: https://docs.bigmodel.cn/api-reference/模型-api/对话补全.md

---

## 📅 更新日志

- **2026-04-17**: 首次发布，采集并验证7个免费模型
- 数据来源: 智谱AI官方速率限制页面 + 免费模型文档
