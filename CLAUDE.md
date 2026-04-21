# API 测试项目 Git 自动化管理

## Git 自动化规则

### 1. 会话开始前
- **必须**读取最近 5 条 git 提交记录：`git log --oneline -5`
- 了解项目当前状态和最近修改

### 2. 任务完成后
- **必须**执行本地 git 提交流程（**不自动 push**）：
  1. `git status` 查看变更
  2. `git diff` 检查具体修改
  3. `git add <相关文件>` 添加变更
  4. `git commit -m "描述任务完成内容"` 提交

### 2.1. Push 策略
- **提交后不自动 push**
- 需要推送时，手动执行：
  ```bash
  # 检查当前分支
  git branch --show-current
  # 确认无误后 push
  git push
  ```
- 如果使用功能分支 (`feature/xxx` 或 `bugfix/xxx`)，push 后创建 PR 合并到 `dev` 或 `main`

### 3. 提交信息格式
```
<类型>: <简要描述>

<详细说明>

类型说明:
- feat: 新功能或模型测试
- test: 模型测试结果
- fix: 修复问题
- docs: 文档更新
- refactor: 代码重构
```

### 4. 文件管理原则
- 测试代码和配置文件必须提交
- API keys 和敏感信息必须忽略（已在 .gitignore）
- 临时文件不提交

### 5. 分支策略
- 主分支：`main`
- 功能分支：`feature/<功能名>`
- 修复分支：`bugfix/<问题>`

## 当前项目结构

```
api_key_test/
├── src/                    # 客户端代码
│   ├── base_client.py      # 基础客户端
│   ├── nvidia_client.py    # NVIDIA 客户端
│   └── platform_registry.py # 平台注册
├── configs/               # 配置文件
│   └── platforms.yaml      # 平台配置
├── scripts/               # 测试脚本
│   └── batch_test.py       # 批量测试
├── docs/                  # 文档
│   └── NVIDIA_免费模型测试记录.md
└── CLAUDE.md              # 本文件
```

## 可用模型状态

### ✅ 正常工作的模型
- `google/gemma-4-31b-it` - 推理模型
- `z-ai/glm4.7` - 推理模型
- `minimaxai/minimax-m2.7` - 普通聊天模型
- `qwen/qwen3-coder-480b-a35b-instruct`
- `deepseek-ai/deepseek-v3.1-terminus`
- `meta/llama-4-maverick-17b-128e-instruct`
- `moonshotai/kimi-k2-instruct-0905`
- `google/gemma-7b`
- `microsoft/phi-3-mini-128k-instruct`
- `stepfun-ai/step-3.5-flash`

### ⚠️ 不稳定的模型
- `z-ai/glm-5.1` - 最新发布的模型（2026-04-18），使用 `--sort-by recent` 可爬到，但可能超时

### ❌ 不可用的模型
- （无）

## 测试流程

### 基础测试流程
1. 先检查模型是否在 `/v1/models` 列表中
2. 测试简单对话（"回复 OK"）
3. 记录响应时间和输出格式
4. 更新测试文档
5. 提交 git

### 爬虫批量测试流程

#### 1. 选择排序方式
NVIDIA 爬虫支持两种排序方式：
- **热度排序**（`--sort-by popular`，默认）：按官方热度权重排序，适合发现稳定、常用的模型
- **最新排序**（`--sort-by recent`）：按发布时间排序，可爬到最新模型（如 GLM-5.1 会排在第1位）

#### 2. 开始爬取
```bash
# 使用热度排序（默认）
python crawler/main.py -n 50

# 使用最新排序
python crawler/main.py -n 50 --sort-by recent
```

爬虫必须提取模型卡片标签：
- 📥 **downloadable** - 模型权重可下载
- 🔓 **free** - 免费API端点
- ⏰ **timeout** - 无法访问

#### 3. 批量测试所有爬取的模型（并发3-5）
#### 4. 记录每个模型的：
- 热度排名（rank）
- 响应时间（response_time）
- 标签信息（is_downloadable, is_free_endpoint, tags）
- 是否可调用（test_status）

#### 5. 生成 Markdown 报告
报告文件（`docs/nvidia/NVIDIA_BATCH_TEST_YYYYMMDD_HHMMSS.md`）必须包含：
- 📈 总体统计（成功率）
- 🏆 最快模型排行榜（Top 10，含标签）
- 🎯 完整测试结果（按实际排序方式显示，标注标签）
- 🔍 爬取信息和原始数据链接

#### 6. 保存 JSON 原始报告
包含完整标签数据，同样带时间戳（`docs/raw-data/nvidia/nvidia_raw_YYYYMMDD_HHMMSS.json`）

#### 7. 提交所有报告文件和更新代码

## 报告格式规则

### Markdown 报告表格必须包含的列
| 热度排名 | 模型ID | 标签 | 响应时间 | 是否可调用/错误详情 |
|----------|--------|------|----------|-------------------|

### 标签映射表
| 图标 | 标签名 | 含义 |
|------|--------|------|
| 📥 | downloadable | 模型权重可下载 |
| 🔓 | free | 免费API端点 |
| ❌ | unknown/timeout | 无法访问或超时 |

### 推荐模型标注
报告中必须标注：
- ✅ **推荐使用的模型**（速度快+稳定+标签清晰）
- ❌ **避免使用的模型**（持续超时或不可用）

## 注意事项

- NVIDIA API 需要 SSL 证书设置
- 推理模型输出在 `reasoning_content`
- 流式响应需要特殊处理
- 每次测试后必须更新文档
- 爬虫必须使用 `--ignore-certificate-errors` 规避 SSL 问题
