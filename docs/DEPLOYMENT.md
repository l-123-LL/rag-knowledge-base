# 部署与验证

> 现状：Docker 相关文件已就绪并做过静态检查，但**本机尚未安装 Docker，没有实机验证过**。
> 下面每一步都写了预期输出，装好 Docker 后按顺序执行即可。

## 安装记录（2026-09-17）

| 项目 | 状态 |
| --- | --- |
| Docker Desktop 安装包 | 已下载到 `D:\DockerDesktopInstaller.exe`（598.9 MB） |
| 安装位置 | `D:\Docker`（静默安装，退出码 0） |
| 版本 | Docker 29.8.0 / Docker Compose v5.5.1（`D:\Docker\resources\bin\docker.exe`） |
| WSL2 组件 | 已执行 `wsl --install --no-distribution`，系统已标记 `RebootPending`，**需要重启电脑后才能用** |
| 引擎状态 | 重启前无法启动（`Docker Desktop is unable to start`），属预期 |

**重启后的验证顺序**：

```powershell
$docker = "D:\Docker\resources\bin\docker.exe"
wsl --status                                   # 能看到 WSL 版本信息即正常
Start-Process "D:\Docker\Docker Desktop.exe"   # 首次启动可能弹出引导页，接受即可
& $docker info --format "{{.ServerVersion}}"   # 打印出版本号即引擎就绪
cd D:\rag知识库
& $docker compose up --build                   # 首次会拉基础镜像并安装依赖，约 2-3 GB，耗时 10-40 分钟
```

首次 `up --build` 之后按第 2 节的验证清单逐条检查。

## 0. 前置

1. 安装 Docker Desktop（Windows），确认 `docker --version` 可用；
2. 确认 `backend/.env` 存在（compose 的 `env_file` 是必需项）。最小内容：

```ini
DEEPSEEK_API_KEY=<你的 Key>
HF_ENDPOINT=https://hf-mirror.com
HF_HOME=D:\rag知识库\models\huggingface
ADMIN_API_KEY=<管理端 Key>
RAG_MIN_SCORE=0.42
```

只想本地演示、不接真实生成模型时，`DEEPSEEK_API_KEY` 可以留空：FAQ 与订单/物流工具都不需要模型，只有知识检索生成会返回 503。

3. 模型权重已缓存到 `models/huggingface`（容器会挂载为 `/app/models`）。没有缓存时首次启动会联网下载约 2.5 GB。

## 1. 启动

```powershell
cd D:\rag知识库
docker compose up --build
```

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 后端 | http://127.0.0.1:8000/docs | 20+ 接口；`/health` 返回 `{"status":"ok"}` |
| 前端 | http://127.0.0.1:5173/ | Nginx 托管静态资源并把 `/api/` 反代到后端 |

`web` 会等 `backend` 通过健康检查后再启动（`depends_on: condition: service_healthy`）。

## 2. 验证清单

```powershell
docker compose ps                       # 两个容器都在运行且健康
curl http://127.0.0.1:8000/health       # {"status":"ok"}

# 关键一步：订单工具在容器里能取到数据（验证 mock 目录已打进镜像）
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" `
  -d '{"question":"订单 SO20260901001 现在什么状态","workflow_mode":"tools"}'

curl http://127.0.0.1:8000/traces/<上一步返回的 trace_id>   # 轨迹可回读
```

如果订单问题返回的是"资料不足/转人工"，说明镜像里没有 `mock/orders.json`（见故障排查）。

## 3. 回滚

```powershell
docker compose down                     # 停止并删除容器；数据在宿主机目录，不会被删
git log --oneline -5                    # 找到上一个可用提交
git checkout <commit> -- backend web    # 只回滚代码，不动文档
docker compose up --build
```

`backend/data` 是宿主机 bind mount，回滚代码不会丢数据。

## 4. 备份与恢复

```powershell
# 方式一：管理员接口打包 data 目录
curl -X POST http://127.0.0.1:8000/backup -H "X-API-Key: <ADMIN_API_KEY>"

# 方式二：直接备份宿主机目录
Copy-Item backend\data "D:\backup\rag-data-$(Get-Date -Format yyyyMMdd)" -Recurse
```

恢复：停止容器 → 用备份覆盖 `backend/data` → 重启。索引、FAQ、会话、工单、轨迹都在这个目录里。

## 5. 故障排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 订单/物流问题答"资料不足" | 镜像缺少 `mock/orders.json` | 确认 `backend/Dockerfile` 有 `COPY mock ./mock`，重建镜像 |
| 容器启动即退出，日志报权限拒绝 | bind mount 属主与非 root 用户不匹配 | 临时给 backend 服务加 `user: root`，或调整宿主目录权限 |
| 首次知识检索特别慢 | 权重没缓存，容器在下载 | 预置 `models/huggingface` 缓存，或配置 `HF_ENDPOINT` 镜像 |
| 前端打不开接口 | Nginx 反代目标写死为 `backend:8000` | 确认两个服务在同一 compose 网络内、服务名就是 `backend` |
| 5173 或 8000 被占用 | 本机已有服务在跑 | 改 compose 端口映射，或先停掉本地 dev server |

## 6. 尚未验证的部分（如实说明）

- 镜像构建与 `docker compose up` 未实机执行（本机无 Docker）；
- 健康检查、条件启动、非 root 运行都只是静态配置，需要实机确认；
- 未做并发压测与容器故障注入，这两项在审计里列为待办。
