# 排序功能使用指南

## 新增功能

从 2026-04-21 开始，NVIDIA 爬虫支持按**热度**或**最新发布时间**排序和爬取模型。

## 使用方式

### 1. 使用 `scripts/test_nvidia.py`

```bash
# 按热度排序（默认） - 爬取最热门的模型
python scripts/test_nvidia.py -n 50 --sort-by popular

# 按最新发布时间排序 - 爬取最新发布的模型（GLM-5.1 会排在第1位！）
python scripts/test_nvidia.py -n 50 --sort-by recent
```

### 2. 使用 `crawler/main.py`

```bash
# 最新排序模式
python crawler/main.py -n 50 --sort-by recent

# 热度排序模式（默认）
python crawler/main.py -n 50 --sort-by popular
```

### 3. 从代码调用

```python
from platforms.nvidia import NvidiaScraper

# 创建爬虫
scraper = NvidiaScraper(headless=True)

# 按最新排序爬取
models = await scraper.scrape(limit=50, sort_by="recent")

# 按热度排序爬取
models = await scraper.scrape(limit=50, sort_by="popular")
```

## 排序选项说明

| sort_by 值 | 说明 | URL 示例 |
|-----------|------|----------|
| `popular` | 按热度排序（官方权重） | `?orderBy=weightPopular:DESC` |
| `recent` | 按最新发布时间排序 | `https://build.nvidia.com/models`（无参数） |

## 验证示例

使用最新排序爬取，前5个模型示例：

```
  #1: glm-5.1 (z-ai)         <-- 最新！April 18, 2026
  #2: glm-4.7 (z-ai)         <-- April 17, 2026
  #3: NVIDIA AI for Media Relighting (nvidia)
  #4: nemotron-3-content-safety (nvidia)
  #5: synthetic-video-detector (nvidia)
```

## 技术细节

- **BaseScraper** 接口已扩展，新增 `sort_by` 和 `sort_order` 参数
- 默认值为 `sort_by="popular"`，保持向后兼容
- 所有平台爬虫已更新签名（智谱爬虫忽略排序参数，因为使用预定义列表）
- 生成的测试报告标记为 "按热度排序"，可根据实际使用的排序方式调整文案

## 注意事项

- 最新排序（recent）**不会**在 URL 中传递 `orderBy` 参数，依赖网站默认排序
- 热度排序会使用 `orderBy=weightPopular:DESC`
- `sort_order` 参数目前固定为 `DESC`，因为两种场景都需要降序
