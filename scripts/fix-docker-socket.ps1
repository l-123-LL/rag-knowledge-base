<#
Docker Desktop 启动报错修复脚本

症状（Docker Desktop 弹窗 / 日志里出现）：
    starting services: initializing Ingest server: listening on unix://C:/Users/<你>/AppData/Local/Docker/run/sailor-ingest.sock:
    rename ...sailor-ingest.sock ...sailor-ingest.sock.stale: The file cannot be accessed by the system.

原因：Docker Desktop 非正常退出（崩溃、强制结束进程、直接重启电脑）后留下的 AF_UNIX socket
文件无法被重命名或删除，导致每次启动都卡在同一步。换成 docker-secrets-engine\engine.sock 也是同一类问题。

做法：结束 Docker/WSL 进程 → 把两个运行时目录整体改名移开（Docker 会重建）→ 恢复设置文件 → 重新启动。

用法（需要管理员权限）：
    powershell -ExecutionPolicy Bypass -File scripts\fix-docker-socket.ps1
#>

$ErrorActionPreference = "Stop"
$dockerDir = Join-Path $env:LOCALAPPDATA "Docker"
$secretsDir = Join-Path $env:LOCALAPPDATA "docker-secrets-engine"
$settingsSource = Join-Path $env:APPDATA "Docker\settings-store.json"
$dockerExe = "D:\Docker\Docker Desktop.exe"

Write-Host "1) 结束 Docker 与 WSL 进程..." -ForegroundColor Cyan
Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "*docker*" -or $_.Name -like "wsl*" -or $_.Name -eq "vpnkit" } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 4
wsl --shutdown 2>&1 | Out-Null
Start-Sleep -Seconds 3

Write-Host "2) 把卡住的运行时目录移开..." -ForegroundColor Cyan
$stamp = Get-Date -Format "yyyyMMddHHmmss"
foreach ($dir in @($dockerDir, $secretsDir)) {
    if (Test-Path $dir) {
        $target = "$dir.stale-$stamp"
        Rename-Item -LiteralPath $dir -NewName (Split-Path $target -Leaf)
        Write-Host "   $dir -> $target"
    }
}

Write-Host "3) 重建目录并恢复设置（保持已接受的服务协议）..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
if (Test-Path $settingsSource) {
    Copy-Item $settingsSource (Join-Path $dockerDir "settings-store.json") -Force
    Write-Host "   已从 $settingsSource 恢复设置"
}

Write-Host "4) 启动 Docker Desktop..." -ForegroundColor Cyan
if (-not (Test-Path $dockerExe)) {
    throw "找不到 $dockerExe，请按实际安装路径修改脚本。"
}
Start-Process -FilePath $dockerExe

$cli = "D:\Docker\resources\bin\docker.exe"
Write-Host "5) 等待引擎就绪（最多 5 分钟）..." -ForegroundColor Cyan
for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 15
    $out = (& $cli info --format "{{.ServerVersion}}" 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $out -notmatch "failed|error|unable") {
        Write-Host "引擎就绪：$out" -ForegroundColor Green
        exit 0
    }
}

Write-Host "引擎仍未就绪，请查看 %LOCALAPPDATA%\Docker\log\host\ 下的日志。" -ForegroundColor Yellow
exit 1
