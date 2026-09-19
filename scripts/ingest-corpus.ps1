# 把 backend/corpus 里的公开语料逐篇导入正在运行的后端。
#
# 用法（在仓库根目录执行）：
#   powershell -ExecutionPolicy Bypass -File scripts/ingest-corpus.ps1
# 可选参数：
#   -BaseUrl http://127.0.0.1:8000  后端地址
#   -CorpusDir backend/corpus       语料目录
#   -EnvFile backend/.env           从这里读 ADMIN_API_KEY（不打印、不写日志）
#
# 幂等：分块 id 由「来源 + 序号 + 内容摘要」生成，重复执行只会跳过已存在的分块。
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$CorpusDir = "backend/corpus",
    [string]$EnvFile = "backend/.env"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw "找不到 $EnvFile，请先从 .env.example 复制并把 ADMIN_API_KEY 填进去"
}

# 只取需要的键，避免把其它密钥带进内存作用域
$adminKey = $null
foreach ($line in Get-Content -LiteralPath $EnvFile) {
    if ($line -match '^\s*ADMIN_API_KEY\s*=\s*(.+?)\s*$') {
        $adminKey = $Matches[1].Trim('"').Trim("'")
    }
}
if ([string]::IsNullOrWhiteSpace($adminKey)) {
    throw "$EnvFile 里的 ADMIN_API_KEY 是空的"
}

$files = Get-ChildItem -LiteralPath $CorpusDir -Filter "*.md" |
    Where-Object { $_.Name -ne "README.md" } |
    Sort-Object Name

if (-not $files) {
    throw "$CorpusDir 下没有可导入的 .md 语料"
}

$total = 0
foreach ($file in $files) {
    # 用 .NET 读文件：Get-Content 返回的字符串会带上 PSPath 等 NoteProperty，
    # ConvertTo-Json 会把它序列化成对象，后端会因为 text 不是字符串直接 422。
    $text = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
    $body = @{
        text     = $text
        source   = $file.BaseName
        doc_key  = $file.BaseName
        version  = 1
    } | ConvertTo-Json

    # 显式转成 UTF-8 字节再发送：Windows PowerShell 5.1 在 -Body 传字符串时
    # 会按本地代码页编码，中文正文会被后端按 UTF-8 解码失败（报 JSON decode error）。
    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $response = Invoke-RestMethod -Uri "$BaseUrl/ingest" -Method Post `
        -Body $bodyBytes -ContentType "application/json; charset=utf-8" `
        -Headers @{ "X-API-Key" = $adminKey }

    $total += $response.chunk_count
    Write-Host ("{0} -> 新增 {1} 个分块" -f $file.Name, $response.chunk_count)
}

Write-Host "本次共新增 $total 个分块"
