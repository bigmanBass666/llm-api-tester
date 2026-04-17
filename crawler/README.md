# NVIDIA 模型批量测试器

基于爬虫的 NVIDIA NIM 模型批量测试框架，支持按官方热度排序测试前N个模型。

## 🚀 特性

- **智能爬取**: 自动从 build.nvidia.com 获取按热度排序的模型列表
- **批量测试**: 支持并发测试多个模型，提高效率
- **详细报告**: 生成包含响应时间、错误信息的详细测试报告
- **异步架构**: 基于 asyncio 的高性能异步测试
- **自动重试**: 智能错误处理和超时管理

## 📁 项目结构

```
crawler/
├── main.py              # 主入口程序
├── models.py            # 模型数据结构和存储
├── scraper.py           # NVIDIA 页面爬虫
├── tester.py            # 模型批量测试器
├── reports/             # 测试报告目录
├── requirements.txt     # Python 依赖
└── README.md            # 说明文档
```

## 🛠️ 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

## 🎯 使用方法

### 1. 快速测试（默认配置）

```bash
python crawler/main.py
```

测试前20个模型，并发数3，超时60秒。

### 2. 自定义参数

```bash
# 测试前50个模型，并发数5
python crawler/main.py -n 50 -c 5

# 仅爬取模型列表，不测试
python crawler/main.py --scrape-only -n 30

# 设置超时时间
python crawler/main.py --timeout 120
```

### 3. 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-n, --number` | 测试的模型数量 | 20 |
| `-c, --concurrency` | 并发测试数量 | 3 |
| `--scrape-only` | 仅爬取模型列表 | False |
| `--timeout` | 单个模型测试超时(秒) | 60 |

## 📊 测试报告

测试完成后会生成详细的 JSON 报告：

```json
{
  "summary": {
    "total": 20,
    "success": 15,
    "failed": 3,
    "timeout": 2
  },
  "successful_models": [
    {
      "rank": 1,
      "id": "qwen/qwen3-coder-480b-a35b-instruct",
      "response_time": 2.34,
      "token_usage": 45
    }
  ],
  "failed_models": [
    {
      "rank": 8,
      "id": "z-ai/glm5",
      "status": "timeout",
      "error": "Connection timeout"
    }
  ]
}
```

报告文件保存在 `crawler/reports/` 目录下。

## 🔧 API 使用

### 基本用法

```python
import asyncio
from crawler.scraper import scrape_top_models
from crawler.tester import test_top_models

# 爬取模型列表
models = await scrape_top_models(30)

# 批量测试
results = await test_top_models(limit=20, concurrency=5)
```

### 自定义测试

```python
from crawler.models import ModelStore
from crawler.tester import ModelTester

# 创建模型存储
store = ModelStore()

# 添加自定义模型
custom_models = [
    {"id": "qwen/qwen3-coder-480b-a35b-instruct", "rank": 1},
    {"id": "google/gemma-4-31b-it", "rank": 2},
]

# 批量测试
tester = ModelTester()
results = await tester.test_batch_models(custom_models, concurrency=3)
```

## ⚠️ 注意事项

1. **网络要求**: 需要稳定的网络连接访问 NVIDIA API
2. **API 限制**: 注意 API 调用频率限制
3. **SSL 证书**: Windows 需要设置 SSL 证书路径
4. **浏览器依赖**: Playwright 需要安装 Chromium
5. **超时设置**: 推理模型可能需要更长的时间

## 🐛 常见问题

### Q: 爬取失败怎么办？
A: 尝试以下方法：
- 检查网络连接
- 增加超时时间
- 使用 `--scrape-only` 查看爬取结果

### Q: 测试速度慢怎么办？
A: 调整并发数：
```bash
python crawler/main.py -c 10  # 增加并发数
```

### Q: 如何查看详细的错误信息？
A: 测试报告会记录详细的错误信息，查看报告文件即可。

## 📈 性能优化建议

1. **合理设置并发数**: 根据网络状况调整，一般3-10为宜
2. **分批测试**: 大量模型时建议分批测试
3. **缓存结果**: 重复测试时可复用之前的爬取结果
4. **监控资源**: 注意内存和CPU使用情况

## 🔗 相关链接

- [NVIDIA NIM API 文档](https://docs.api.nvidia.com/nim/)
- [build.nvidia.com](https://build.nvidia.com/models)
- [项目主文档](../README.md)

---

**最后更新**: 2026-04-14