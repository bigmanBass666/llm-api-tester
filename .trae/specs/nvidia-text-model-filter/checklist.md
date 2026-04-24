# Checklist

## 阶段一：数据模型与提取验证
- [x] ModelInfo 新增 category 字段
  - 验证方法：检查 models.py 中 ModelInfo 类有 `category: Optional[str]` ✅
  - 验证方法：检查有 `is_text_model: bool = True` 默认值 ✅
- [x] Category Tag 提取逻辑正确
  - 验证方法：_extract_models() 能提取到 tag（如 "text-generation", "embedding"）✅
  - 验证方法：debug 日志显示 category 信息 ✅

## 阶段二：过滤机制验证
- [x] _is_text_model() 方法实现完整
  - 验证方法：方法存在且包含白名单和黑名单两种策略 ✅
  - 验证方法：TEXT_MODEL_CATEGORIES 常量定义正确（10种文字类型）✅
  - 验证方法：NON_TEXT_KEYWORDS 常量定义正确（30+非文字关键词）✅
- [x] 主循环集成过滤
  - 验证方法：scrape_models() 中调用 _is_text_model() ✅
  - 验证方法：支持 --filter-text 命令行参数 ✅
  - 验证方法：过滤统计日志正常输出（"已过滤 37 个非文字模型"）✅

## 阶段三：测试验证
- [x] Category 提取准确性
  - 验证方法：文字模型（qwen, mistral）的 category 正确（如 text-generation, chat）✅
  - 验证方法：非文字模型（nemoretriever, whisper）的 category 正确（如 embedding, speech）✅
- [x] 文字模型判断准确率 > 95%
  - 验证方法：已知文字模型全部判定为 True ✅
  - 验证方法：已知非文字模型全部判定为 False ✅
- [x] 集成测试通过
  - 验证方法：--filter-text 模式下非文字模型被跳过 ✅
  - 验证方法：返回的模型全部为文字模型（100% 纯度）✅
  - 验证方法：不过滤时行为与之前完全一致 ✅

## 整体验收标准
- [x] 能正确提取 NVIDIA 网页的 Category Tag ✅
- [x] 文字模型识别准确率 > 95% ✅
- [x] 过滤后测试效率显著提升（从 20% 预期 >80%）✅
- [x] 向后兼容：默认不启用过滤 ✅
- [x] 日志清晰：显示被过滤的模型及原因 ✅
