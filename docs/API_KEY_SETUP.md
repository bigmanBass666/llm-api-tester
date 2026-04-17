# 🔐 API Key 配置与管理指南

## 📋 目录

- [概述](#概述)
- [首次配置](#首次配置)
- [日常使用](#日常使用)
- [团队协作](#团队协作)
- [安全应急响应](#安全应急响应)
- [故障排除](#故障排除)

---

## 概述

### 设计原则

1. **敏感信息零存储**：API keys 绝不提交到 git 仓库
2. **环境隔离**：开发、测试、生产使用不同配置
3. **降级策略**：环境变量 > .env 文件 > 报错
4. **清晰报错**：缺少 key 时提供明确的配置指引

### 支持平台

| 平台 | 环境变量名 | 配置示例 |
|------|-----------|---------|
| NVIDIA NIM | `NVIDIA_API_KEY` | `nvapi-xxxxxxxx` |
| 智谱 AI | `ZHIPU_API_KEY` | `508431.xxxxx` |
| 阿里云百炼 | `DASHSCOPE_API_KEY` | `sk-xxxxx` |
| 腾讯云混元 | `TENCENTCLOUD_SECRET_ID` + `TENCENTCLOUD_SECRET_KEY` | 需两个变量 |

---

## 首次配置

### 步骤 1：复制配置模板

```bash
cp .env.example .env.local
```

### 步骤 2：填入 API keys

编辑 `.env.local`：

```env
# 必填：根据你要使用的平台
NVIDIA_API_KEY=nvapi-your_real_key_here
ZHIPU_API_KEY=508431.your_real_key_here
```

### 步骤 3：验证配置

```bash
# 测试环境变量加载
python -c "from src.config_loader import ConfigLoader; ConfigLoader.load_env('.env.local'); print('✅ NVIDIA:', ConfigLoader.get_api_key('nvidia')[:10])"

# 完整测试（会真正调用 API）
python crawler/zhipu_speed_test.py  # 智谱测速
python crawler/simple_tester.py      # NVIDIA 简测
```

### 步骤 4：提交配置（仅模板）

```bash
# .env.local 已在 .gitignore 中，无需提交
git add .env.example
git commit -m "chore: 添加 env 配置模板"
git push
```

---

## 日常使用

### 代码中获取 API Key

所有客户端已自动集成 `ConfigLoader`，无需手动处理：

```python
# 方式 1：直接使用便捷函数（推荐）
from src.config_loader import get_api_key
api_key = get_api_key('nvidia')

# 方式 2：使用 ConfigLoader 类
from src.config_loader import ConfigLoader
ConfigLoader.load_env('.env.local')  # 启动时调用一次
api_key = ConfigLoader.get_api_key('zhipu')

# 方式 3：通过平台注册表创建客户端（完全透明）
from src.platform_registry import create_client
client = create_client('nvidia')  # 自动加载 .env 中的 key
```

### 测试脚本运行

所有测试脚本已自动加载配置，只需确保 `.env.local` 存在：

```bash
# 智谱 AI 测速（自动使用 ZHIPU_API_KEY）
python crawler/zhipu_speed_test.py

# NVIDIA 批量测试（自动使用 NVIDIA_API_KEY）
python crawler/simple_tester.py
```

### 切换不同配置

开发 vs 生产环境：

```bash
# 开发环境（使用 .env.local）
export APP_ENV=development
python your_script.py

# 生产环境（使用系统环境变量，无 .env 文件）
export APP_ENV=production
export NVIDIA_API_KEY=prod_key_here
python your_script.py
```

---

## 团队协作

### 新成员加入流程

1. **克隆仓库**
   ```bash
   git clone <your-repo>
   cd api_key_test
   ```

2. **复制配置模板**
   ```bash
   cp .env.example .env.local
   ```

3. **填入自己的 API keys**（从各平台获取）

4. **验证配置**
   ```bash
   python tests/test_speed_tester_framework.py
   ```

5. **开始开发**
   ```bash
   git pull origin main
   ```

### .gitignore 规则

项目已配置完整的 ignore 规则：

```gitignore
# 敏感信息
.env
.env.*
!.env.example  # 模板文件允许提交
secrets.json
*.key
*.pem

# 虚拟环境
venv/

# 测试输出（可能包含敏感响应）
crawler/reports/
docs/platforms/raw-data/
logs/

# 其他临时文件
.playwright-mcp/
*.log
```

**重要**：`.env.local` 是个人专属，绝对不要 `git add`！

---

## 安全应急响应

### 🔴 API Key 泄露处理

如果发现 API key 已提交到 git（本地或远程）：

#### 情况 A：仅本地仓库（未 push）

1. 立即撤销泄露的 key（在对应平台侧）
2. 生成新 key
3. 更新 `.env.local`
4. **清理 git 历史**（可选但推荐）：
   ```bash
   # 方法1: BFG Repo-Cleaner（最简单）
   java -jar bfg.jar --replace-text passwords.txt .
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive

   # 方法2: git filter-repo
   git filter-repo --replace-text <(echo "old_key==>[REMOVED]")
   ```

#### 情况 B：已推送到远程

1. **立即撤销泄露的 key**（第一优先！）
2. 生成新 key 并更新 `.env.local`
3. 通知所有协作者重新克隆仓库（历史已重写）
4. **强制推送清理后的历史**：
   ```bash
   git push --force --all
   git push --force --tags
   ```

**注意**：重写历史会影响所有协作者，务必提前沟通！

### 定期安全审计

每月检查一次：

```bash
# 1. 扫描代码中是否意外包含硬编码 key
grep -r "nvapi-" src/ crawler/ examples/ || echo "✅ 无硬编码 NVIDIA key"

# 2. 检查 .gitignore 是否生效
git status --ignored | grep ".env" || echo "✅ .env 已被忽略"

# 3. 验证环境变量加载正常
python -c "from src.config_loader import ConfigLoader; print('✅ ConfigLoader 正常')"
```

---

## 故障排除

### 错误：`缺少 nvidia 的 API Key`

**原因**：未设置 `NVIDIA_API_KEY` 环境变量或 `.env.local` 文件

**解决**：
1. 检查 `.env.local` 是否存在且有 `NVIDIA_API_KEY=xxx`
2. 运行 `source .env.local` 或重启终端
3. 验证：`echo $NVIDIA_API_KEY`（Linux/Mac）或 `echo %NVIDIA_API_KEY%`（Windows）

### 错误：`SSL 证书验证失败`

**Windows 常见问题**，解决方法：

1. 安装 certifi：
   ```bash
   pip install certifi
   ```

2. 在 `.env.local` 中添加：
   ```env
   SSL_CERT_FILE=D:/apps/python312/Lib/site-packages/certifi/cacert.pem
   REQUESTS_CA_BUNDLE=D:/apps/python312/Lib/site-packages/certifi/cacert.pem
   ```

3. 或使用 `verify=False`（仅测试环境）：
   ```python
   client = OpenAI(..., http_client=httpx.Client(verify=False))
   ```

### 错误：`.env 文件被 git 跟踪`

**原因**：`.env` 或 `.env.local` 已被提交

**解决**：
```bash
# 1. 从 git 移除（保留本地文件）
git rm --cached .env .env.local

# 2. 确保 .gitignore 包含 .env 和 .env.local

# 3. 提交
git commit -m "chore: 移除敏感文件"
```

---

## 附录

### 环境变量优先级

加载顺序（后加载的覆盖先加载的）：

1. 系统环境变量（最高）
2. `.env.local`（个人开发）
3. `.env.development`（团队开发）
4. `.env`（默认）

### 配置文件说明

| 文件 | 用途 | 是否提交 | 内容 |
|------|------|---------|------|
| `.env.example` | 模板 | ✅ 是 | 空值 + 注释 |
| `.env.local` | 个人开发 | ❌ 否 | 真实 key |
| `.env.production` | 生产环境 | ❌ 否 | 生产 key |
| `configs/platforms.yaml` | 平台元数据 | ✅ 是 | 并发、分类等 |

### 参考资源

- [python-dotenv 文档](https://saurabh-kumar.com/python-dotenv/)
- [12-Factor App 配置管理](https://12factor.net/zh_cn/config)
- 项目 CLAUDE.md 中的 Git 工作流规范

---

**🛡️ 记住：API keys 是敏感信息，保护它们就是保护你的账户和资源！**
