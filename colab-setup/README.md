# Google Colab 自动化 - Flux2 边界测试

## 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| Clash 代理 | ✅ 运行中 | 系统代理 127.0.0.1:3067 |
| agent-browser | ✅ 可用 | 可访问 Colab（需代理） |
| Colab MCP Server | ✅ 已安装 | 位于项目虚拟环境中 |
| Google 登录 | ⚠️ 需手动 | 安全风控阻止自动化登录 |
| MCP 配置 | ✅ 已更新 | `.claude.json` 已指向 Windows 路径 |

---

## 快速开始

### 1. 重载 MCP 配置

用户醒后，在 Claude Code 中执行：
```
/mcp
```
这将重载 MCP 配置，启用 `colab-mcp`。

### 2. 手动登录 Google（一次性）

由于 Google 安全风控，**首次**需要在用户自己的 Chrome 中登录：

1. 确保 Clash 在运行（系统托盘有图标）
2. 打开 Chrome，访问 https://colab.research.google.com
3. 使用账号 `bigmanbass666@gmail.com` 登录
4. 登录成功后，后续可通过 Colab MCP 自动化

### 3. 使用 Colab MCP

登录后，Claude Code 可以直接控制 Colab：

```
在 Colab 上创建一个 FLUX 边界测试 notebook，使用 T4 GPU
```

Colab MCP 会自动：
- 打开 Colab 空白 notebook
- 连接 WebSocket
- 创建代码单元格
- 安装依赖
- 运行代码

---

## 代理配置

### Clash（当前使用）

- 可执行文件：`D:/apps/Clash/Clash for Windows.exe`
- 系统代理端口：`127.0.0.1:3067`
- API 控制：`127.0.0.1:49689`
- 当前节点：`🇯🇵 免费-日本2-Ver.7`

### 切换节点（如需）

```bash
# 查看节点
curl -s "http://127.0.0.1:49689/proxies" -H "Authorization: Bearer 1333421e-42fe-441f-8e16-f55d37c8d3b9"

# 切换节点
curl -s -X PUT "http://127.0.0.1:49689/proxies/%F0%9F%94%B0%20%E9%80%89%E6%8B%A9%E8%8A%82%E7%82%B9" \
  -H "Authorization: Bearer 1333421e-42fe-441f-8e16-f55d37c8d3b9" \
  -H "Content-Type: application/json" \
  -d '{"name":"🇯🇵 免费-日本1-Ver.6"}'
```

---

## agent-browser 使用

当需要浏览器自动化时（不依赖 MCP）：

```bash
# 启动（带代理）
agent-browser open https://colab.research.google.com --proxy "http://127.0.0.1:3067"

# 查看页面
agent-browser snapshot -i

# 截图
agent-browser screenshot colab.png --annotate

# 关闭
agent-browser close --all
```

---

## Colab 硬件规格

| 资源 | Colab Free | Colab Pro |
|------|-----------|-----------|
| GPU | T4 (16GB) | A100 (40GB) |
| RAM | ~12GB | ~25GB |
| 磁盘 | ~78GB | ~166GB |
| 会话时长 | ~12小时 | ~24小时 |
| 空闲断开 | 90分钟 | 90分钟 |

---

## FLUX on Colab

### 推荐配置

```python
# Cell 1: 安装依赖
!pip install -q diffusers transformers accelerate torch

# Cell 2: 加载模型 (T4 16GB)
from diffusers import FluxPipeline
import torch

pipe = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    torch_dtype=torch.bfloat16,
    variant="fp16"
)
pipe = pipe.to("cuda")

# Cell 3: 生成图像
image = pipe(
    prompt="a beautiful landscape",
    height=512,
    width=512,
    guidance_scale=3.5,
    num_inference_steps=20
).images[0]

image.save("output.png")
```

### T4 VRAM 限制

| 配置 | VRAM | 可行性 |
|------|------|--------|
| FLUX.1-dev FP16 | ~24GB | ❌ T4 不够 |
| FLUX.1-dev NF4 | ~15GB | ⚠️ 边缘 |
| FLUX.1-schnell | ~12GB | ✅ 可行 |
| SDXL | ~6-8GB | ✅ 轻松 |
| SD 1.5 | ~2-4GB | ✅ 极轻松 |

---

## 问题排查

### Google 登录被拒绝

**现象**：输入邮箱后显示"无法登录"
**原因**：Google 检测到异常登录（代理 IP + 新浏览器指纹）
**解决**：
1. 在用户自己的 Chrome 中手动登录
2. 或使用其他代理节点
3. 或等待 24 小时后重试

### Colab MCP 无法启动

**检查**：
```bash
# 虚拟环境是否存在
ls .venv/Scripts/colab-mcp.exe

# 直接运行测试
.claude/../.venv/Scripts/colab-mcp.exe --help
```

### agent-browser 超时

**检查代理**：
```bash
curl -s -o /dev/null -w "%{http_code}" --proxy "http://127.0.0.1:3067" https://colab.research.google.com
```
应返回 `200`。

---

## 相关资源

- [Colab MCP 官方仓库](https://github.com/googlecolab/colab-mcp)
- [Colab CLI 官方仓库](https://github.com/googlecolab/google-colab-cli)
- [Colab 调研报告](../docs/colab_research_report.md)
- [Kaggle/云部署分析](../docs/kaggle_cloud_deployability_analysis.md)
