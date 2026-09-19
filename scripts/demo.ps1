# 一键起演示：拉容器 → 等健康检查 → 索引为空就导入语料 → 打开页面。
#
# 用法（仓库根目录）：
#   powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
# 可选参数：
#   -SkipIngest   不导入语料（只起服务）
#   -NoBrowser    不自动打开浏览器
#
# 注意：脚本存为**带 BOM 的 UTF-8**，否则 Windows PowerShell 5.1 会把中文按 GBK 读。
param(
    [switch]$SkipIngest,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Wait-Healthy {
    param([string]$Url, [int]$TimeoutSeconds = 180)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri $Url -TimeoutSec 3
            if ($response.status -eq "ok") { return $true }
        } catch {
            Start-Sleep -Seconds 3
        }
    }
    return $false
}

Write-Host "[1/4] 启动容器（首次会构建镜像，可能要几分钟）..." -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose 启动失败，先确认 Docker Desktop 在运行" }

Write-Host "[2/4] 等待后端健康检查..." -ForegroundColor Cyan
if (-not (Wait-Healthy -Url "http://127.0.0.1:8000/health")) {
    throw "后端 180 秒内没有就绪，用 docker compose logs backend 查看原因"
}
Write-Host "      后端就绪" -ForegroundColor Green

if (-not $SkipIngest) {
    Write-Host "[3/4] 检查索引..." -ForegroundColor Cyan
    $stats = Invoke-RestMethod -Uri "http://127.0.0.1:8000/stats"
    if ($stats.chunk_count -gt 0) {
        Write-Host ("      已有 {0} 个分块，跳过导入" -f $stats.chunk_count) -ForegroundColor Green
    } else {
        Write-Host "      索引为空，导入 backend/corpus（74 个分块，CPU 上约 2 分钟）..."
        & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "ingest-corpus.ps1")
        if ($LASTEXITCODE -ne 0) { throw "语料导入失败" }
    }
} else {
    Write-Host "[3/4] 按参数要求跳过语料导入" -ForegroundColor Yellow
}

Write-Host "[4/4] 打开页面..." -ForegroundColor Cyan
if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:5173/"
}

Write-Host ""
Write-Host "  用户端（客服问答） : http://127.0.0.1:5173/" -ForegroundColor Green
Write-Host "  后端接口文档       : http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  停止服务           : docker compose down" -ForegroundColor DarkGray
Write-Host ""
