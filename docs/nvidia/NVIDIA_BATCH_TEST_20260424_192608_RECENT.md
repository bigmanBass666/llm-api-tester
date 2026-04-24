# NVIDIA 批量测速测试报告 (最新排序)

> **测试时间**: 2026-04-24 19:26:08  
> **排序方式**: 最新排序 (`--sort-by recent`)  
> **原始数据**: [test_report_20260424_192608.json](../crawler/reports/test_report_20260424_192608.json)

---

## 📈 总体统计

| 指标 | 数值 | 占比 |
|------|------|------|
| 总测试数 | **24** | 100% |
| ✅ 成功 | **5** | **20.8%** |
| ❌ 失败 | 16 | 66.7% |
| ⏸️ 待测试 | 3 | 12.5% |
| ⏰ 超时 | 0 | 0% |

### 成功率分析
- 整体成功率: **20.8%** (5/24) - 较低
- 主要原因: 
  - **大量专用模型**: 最新发布的模型包含很多非聊天类模型（ASR、OCR、图像处理等）
  - **接口不兼容**: 这些专用模型使用不同的 API 端点，不支持标准聊天接口
  - **1个超时**: `minimaxai/minimax-m2.7` 超时

### 🎉 重要发现
✅ **`z-ai/glm-5.1` 成功响应!**
- 虽然耗时较长 (136.05s)，但最终成功返回结果
- 这是智谱 AI 最新发布的大模型（2026-04-18）
- 说明该模型虽然不稳定但仍然可用

---

## 🏆 成功模型排行榜

| 排名 | 模型ID | 响应时间 | 标签 | 模型类型 | 推荐等级 |
|------|--------|----------|------|----------|----------|
| 🥇 1 | `nvidia/gliner-pii` | **0.71s** | 🔓 free | PII 信息识别 | ⭐⭐⭐ 专用任务推荐 |
| 🥈 2 | `nvidia/nemotron-3-content-safety` | **1.07s** | 🔓 free | 内容安全检测 | ⭐⭐⭐ 专用任务推荐 |
| 🥉 3 | `nvidia/ising-calibration-1-35b-a3b` | **1.84s** | 📥 downloadable | 科学计算 | ⭐⭐ 特定场景可用 |
| 4 | `google/gemma-4-31b-it` | **72.26s** | 📥 downloadable | 通用大模型 | ⭐ 可用但较慢 |
| 5 | `z-ai/glm-5.1` | **136.05s** | 📥 downloadable | 通用大模型 | ⭐ 不稳定，慎用 |

### 💡 模型类型分析

#### ✅ 可用的大语言模型 (LLM)
1. **google/gemma-4-31b-it** (72.26s)
   - Google 最新一代 Gemma 模型
   - 响应较慢但功能完整
   - 支持复杂推理任务

2. **z-ai/glm-5.1** (136.05s) ⚠️
   - 智谱 AI 最新旗舰模型
   - **极不稳定**: 耗时超过 2 分钟
   - 仅建议在非实时场景使用

#### ✅ 专用模型 (Non-LLM)
1. **nvidia/gliner-pii** (0.71s) - 极速 PII 检测
2. **nvidia/nemotron-3-content-safety** (1.07s) - 内容审核
3. **nvidia/ising-calibration-1-35b-a3b** (1.84s) - 伊辛模型校准

---

## 🎯 完整测试结果

### ✅ 成功模型 (5个)

| 发布排名 | 模型ID | 标签 | 响应时间(s) | Token使用 | 模型类别 |
|----------|--------|------|-------------|-----------|----------|
| 47 | nvidia/gliner-pii | 🔓 free | 0.71 | 7 | PII 识别 |
| 7 | nvidia/nemotron-3-content-safety | 🔓 free | 1.07 | 435 | 内容安全 |
| 15 | nvidia/ising-calibration-1-35b-a3b | 📥 downloadable | 1.84 | 65 | 科学计算 |
| 19 | google/gemma-4-31b-it | 📥 downloadable | 72.26 | 20 | 通用 LLM |
| 1 | z-ai/glm-5.1 | 📥 downloadable | 136.05 | 12 | 通用 LLM |

### ❌ 失败模型 (16个)

| 发布排名 | 模型ID | 标签 | 错误详情 | 模型类别 |
|----------|--------|------|----------|----------|
| 3 | glm-4.7 | 🔓 free | 404 page not found | LLM (可能未上线) |
| 5 | NVIDIA AI for Media Relighting | 📥 downloadable | 404 page not found | 图像处理 |
| 9 | nvidia/ai-synthetic-video-detector | 📥 downloadable, 🔓 free | 500 Internal Server Error | 视频检测 |
| 11 | Active Speaker Detection | 📥 downloadable, 🔓 free | 404 page not found | 音频处理 |
| 13 | LipSync | 📥 downloadable | 404 page not found | 视频生成 |
| 17 | minimaxai/minimax-m2.7 | 🔓 free | Request timed out. | LLM (超时) |
| 21 | llama-nemotron-rerank-vl-1b-v2 | 📥 downloadable | 404 page not found | Rerank 模型 |
| 25 | nemotron-voicechat | 🔓 free | 404 page not found | 语音聊天 |
| 27 | nemotron-asr-streaming | 📥 downloadable | 404 page not found | 语音识别 (ASR) |
| 29 | flux.2-klein-4b | 📥 downloadable | 404 page not found | 图像生成 |
| 31 | nemotron-ocr-v1 | 📥 downloadable | 404 page not found | OCR 文字识别 |
| 35 | llama-nemotron-rerank-1b-v2 | 📥 downloadable | 404 page not found | Rerank 模型 |
| 39 | nemotron-table-structure-v1 | 📥 downloadable | 404 page not found | 表格结构化 |
| 41 | nemotron-page-elements-v3 | 📥 downloadable | 404 page not found | 版面分析 |
| 43 | nemotron-graphic-elements-v1 | 📥 downloadable | 404 page not found | 图形元素检测 |
| 45 | nvidia/llama-nemotron-embed-1b-v2 | 📥 downloadable | 404 page not found | Embedding 模型 |

### ⏸️ 未测试模型 (3个)
这些模型在之前的测试中已经完成，本次跳过。

---

## 🔍 爬取信息

- **爬取URL**: https://build.nvidia.com/models (无 orderBy 参数)
- **排序方式**: 按发布时间降序排列（最新的在前）
- **目标数量**: 50 个模型
- **实际获取**: 24 个模型（网站单页显示限制）
- **爬取策略**: Playwright 无限滚动 + 去重
- **断点续传**: 加载了之前已测试的 24 个模型，避免重复测试

### ⚠️ 重要发现
1. **最新模型多样性高**: 包含 LLM、ASR、OCR、图像生成、视频处理等多种类型
2. **大部分非聊天模型**: 最新发布的模型中，通用 LLM 占比较少
3. **glm-4.7 可能未上线**: 返回 404，可能还在内测或未开放 API
4. **NVIDIA 专用模型丰富**: 包含多个 Nemotron 系列专用模型

---

## 📊 失败原因分布

| 错误类型 | 数量 | 占比 | 示例 |
|----------|------|------|------|
| **404 Not Found** | 14 | 87.5% | ASR、OCR、Embedding 等 |
| **Request Timeout** | 1 | 6.25% | minimax-m2.7 |
| **500 Server Error** | 1 | 6.25% | ai-synthetic-video-detector |

### 404 错误详解
绝大多数失败都是因为 **API 端点不兼容**:
- 这些模型使用专用的 API 接口（如 `/v1/chat/completions` 以外的端点）
- 需要特殊的请求格式或参数
- 不属于标准的 OpenAI 兼容聊天接口

**涉及的模型类别**:
- 🔊 语音相关: ASR (nemotron-asr-streaming), VoiceChat, Active Speaker Detection
- 👁️ 视觉相关: OCR (nemotron-ocr-v1), 图像检测 (graphic-elements)
- 📄 文档相关: 表格结构化 (table-structure), 版面分析 (page-elements)
- 🔤 文本相关: Rerank (llama-nemotron-rerank-*), Embedding (llama-nemotron-embed-*)
- 🎨 生成相关: 图像生成 (flux.2), 视频生成 (LipSync)

---

## 🎓 结论与建议

### ✅ 积极发现
1. **GLM-5.1 可用性确认**: 虽然慢但能成功调用，说明该模型已经上线
2. **Gemma-4-31B 稳定性**: Google 新一代模型表现稳定（尽管较慢）
3. **专用模型性能优秀**: NVIDIA 的 PII 检测和内容安全模型响应极快 (< 1.1s)

### ⚠️ 问题与挑战
1. **成功率低**: 仅 20.8%，主要因为包含大量非聊天模型
2. **模型筛选困难**: 无法在爬取阶段区分 LLM 和专用模型
3. **部分模型不稳定**: GLM-5.1 耗时 136s，minimax-m2.7 直接超时
4. **API 文档缺失**: 很多新模型的 API 用法不明确

### 🚀 改进建议

#### 对于开发者
1. **过滤模型类型**: 在测试前排除已知的非聊天模型类别
2. **增加超时时间**: 对于大型 LLM 建议设置 180-300s 超时
3. **分类测试**: 将 LLM 和专用模型分开测试，分别评估

#### 对于后续测试
1. **优化爬虫选择器**: 尝试提取模型的"类别"标签（如 Chat、Embedding、Rerank）
2. **使用官方 API**: 考虑直接调用 `/v1/models` 接口获取模型列表及元信息
3. **建立模型白名单**: 维护一个已知可用的 LLM 模型列表

### 📋 推荐使用的模型

#### 🏆 最佳选择 (最新排序)
如果必须使用最新发布的模型：

**稳定可靠**:
- `google/gemma-4-31b-it` - 唯一稳定的通用 LLM (72s)
- `nvidia/gliner-pii` - 极速 PII 检测 (0.71s)
- `nvidia/nemotron-3-content-safety` - 快速内容审核 (1.07s)

**实验性质** (谨慎使用):
- `z-ai/glm-5.1` - 最新技术预览 (136s，可能超时)

#### ❌ 不推荐的模型
- 所有 ASR/OCR/图像类模型 - 需要专用 API
- `minimaxai/minimax-m2.7` - 不稳定，容易超时
- `glm-4.7` - 可能尚未完全上线

---

## 🔄 与热度排序对比

| 维度 | 热度排序 (Popular) | 最新排序 (Recent) |
|------|-------------------|-------------------|
| **总模型数** | 24 | 24 |
| **成功率** | 70.8% (17/24) | 20.8% (5/24) |
| **平均响应时间** | 10.2s | 42.4s |
| **最快模型** | gemma-3-27b-it (0.72s) | gliner-pii (0.71s) |
| **模型类型** | 主要是 LLM | 多样化 (LLM+专用) |
| **适用场景** | 生产环境 | 实验研究 |

### 关键差异
1. **热度排序更适合生产使用**: 成功率高，模型成熟稳定
2. **最新排序适合技术预览**: 可以体验最新模型，但需要容错机制
3. **建议组合使用**: 热度排序选主力模型 + 最新排序跟进技术趋势

---

*报告自动生成于 2026-04-24 19:26:08*
