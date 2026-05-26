# Google Colab MCP 快速启动脚本
# 用法: .\start_colab_mcp.ps1

$ProjectDir = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectDir ".venv\Scripts\colab-mcp.exe"
$LogDir = Join-Path $env:TEMP "colab-mcp-logs"

# 检查虚拟环境
if (-not (Test-Path $VenvPath)) {
    Write-Error "colab-mcp.exe not found at: $VenvPath"
    Write-Host "请先运行: uv venv .venv && uv pip install git+https://github.com/googlecolab/colab-mcp"
    exit 1
}

# 确保日志目录存在
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "Starting Colab MCP Server..." -ForegroundColor Green
Write-Host "Executable: $VenvPath" -ForegroundColor Cyan
Write-Host "Log dir: $LogDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "使用说明:" -ForegroundColor Yellow
Write-Host "1. 在 Claude Code 中执行 /mcp 重载配置" -ForegroundColor White
Write-Host "2. 说: '连接到 Colab' 或 '在 Colab 上创建 notebook'" -ForegroundColor White
Write-Host "3. 首次使用需在浏览器中登录 Google" -ForegroundColor White
Write-Host ""

# 启动 MCP Server
& $VenvPath --log $LogDir --enable-proxy
