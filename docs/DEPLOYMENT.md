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
| 启动后第一次导入/知识检索要等 30 秒以上 | 容器内首次加载嵌入模型，且会向 HuggingFace 发校验请求 | compose 已设 `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`（权重通过 volume 预置）；确认 `models/huggingface` 已缓存权重 |
| 容器启动即退出，日志报权限拒绝 | bind mount 属主与非 root 用户不匹配 | 临时给 backend 服务加 `user: root`，或调整宿主目录权限 |
| 首次知识检索特别慢 | 权重没缓存，容器在下载 | 预置 `models/huggingface` 缓存，或配置 `HF_ENDPOINT` 镜像 |
| 前端打不开接口 | Nginx 反代目标写死为 `backend:8000` | 确认两个服务在同一 compose 网络内、服务名就是 `backend` |
| 5173 或 8000 被占用 | 本机已有服务在跑 | 改 compose 端口映射，或先停掉本地 dev server |

## 6. 实机验证结果（2026-09-17）

| 检查项 | 结果 |
| --- | --- |
| `docker compose up --build` | 通过；`rag-backend` 与 `rag-web` 均构建成功 |
| 容器状态 | `rag-backend` Up **healthy**；`rag-web` Up |
| `/health` | `{"status":"ok"}` |
| **订单工具（验证 mock 已打进镜像）** | `model=order_lookup`，返回真实订单数据 → `COPY mock ./mock` 生效 |
| `GET /traces/{id}` | 通过，`mode=tools`、`tool_calls=1`、延迟 3 ms |
| 前端 `http://127.0.0.1:5173/` | HTTP 200，页面正常挂载 |
| 容器内运行用户 | `uid=1000(app)`，非 root |
| 镜像体积 | `rag-backend` 2.27 GB（CPU 版 torch）、`rag-web` 73.9 MB |
| 高风险写操作审批 | 提交退款申请只生成审批单（`pending`）；`GET /approvals` 需管理员 Key（无 Key 返回 401）；批准后 `status=executed` 并建单；重复批准返回同一工单（幂等） |

## 7. 实机踩到的三个坑（已修）

**坑一：Docker Desktop 反复报 `unable to start`，日志里是 socket 无法重命名**

```
starting services: initializing Ingest server: listening on unix://C:/Users/.../Docker/run/sailor-ingest.sock:
rename ...sailor-ingest.sock ...sailor-ingest.sock.stale: The file cannot be accessed by the system.
```

原因是 Docker 非正常退出后留下的 AF_UNIX socket 文件无法被重命名或删除。修法：结束所有 Docker 进程 → 把 `%LOCALAPPDATA%\Docker` 和 `%LOCALAPPDATA%\docker-secrets-engine` 整个目录改名移开（Docker 会重建）→ 重新启动。注意设置文件 `settings-store.json` 在 `%LOCALAPPDATA%\Docker` 下，移开后首次启动需要重新接受一次服务协议。

**坑二：WSL2 需要重启才生效**

`wsl --install --no-distribution` 之后系统会标记 `RebootPending`，重启前 Docker 引擎无法启动；重启后还需要 `wsl --set-default-version 2`。

**坑三：Linux 上默认装的是 CUDA 版 torch**

`pip install sentence-transformers` 会连带拉入 `nvidia-*` 系列（数 GB），而这些在这个项目里完全用不到。Dockerfile 里改成先用 `--index-url https://download.pytorch.org/whl/cpu` 装 CPU 版 torch，再装其余依赖；镜像因此只有 2.27 GB。

另外注意 pip 源：本机实测**清华源不可达**，而容器内访问官方 `pypi.org` 正常（1.6 秒），所以 `PIP_INDEX_URL` 默认留空走官方源，需要时再覆盖。

## 8. 并发压测（2026-09-19 实测）

脚本：`backend/evaluation/load_test.py`（默认只打不依赖外部模型的路径，零 API 花费）

```powershell
# 默认限流（120 次/分钟/IP）下的表现
python -m evaluation.load_test --url http://127.0.0.1:8001 --concurrency 1,5,10,20 --requests 40

# 关掉限流后的原始吞吐（原生启动时用 RATE_LIMIT_PER_MINUTE=0；
# 容器方式用 docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d）
python -m evaluation.load_test --url http://127.0.0.1:8001 --concurrency 1,10,20,40,80 --requests 120
```

**默认限流开启时**（单实例，订单/FAQ/转人工路径）：

| 并发 | 成功 | P95 | 吞吐 | 状态码 |
| --- | --- | --- | --- | --- |
| 1 | 40/40 | 60.5 ms | 14.1 RPS | 200 |
| 5 | 40/40 | 52.3 ms | 133.5 RPS | 200 |
| 10 | 40/40 | 80.7 ms | 166.5 RPS | 200 |
| 20 | 0/40 | 69.0 ms | 325.0 RPS | **429**（限流生效） |

**关闭限流后的容量曲线**：

| 并发 | 成功 | P95 | 吞吐 |
| --- | --- | --- | --- |
| 1 | 120/120 | 52.6 ms | 24.9 RPS |
| 10 | 120/120 | 81.9 ms | 177.0 RPS |
| 20 | 120/120 | 125.6 ms | 182.0 RPS |
| 40 | 120/120 | 210.4 ms | 183.8 RPS |
| 80 | 120/120 | 350.8 ms | 164.0 RPS |

结论：**600 次请求零错误**；吞吐在并发 20 左右饱和（约 180 RPS），之后延迟线性上升、吞吐略降。默认限流 120 次/分钟会先于容量上限触发，这是设计行为而不是缺陷。

注意口径：以上是**不调用外部模型**的路径（订单 / FAQ / 转人工）。知识问答要等 DeepSeek 生成（首 token 2.5–3 秒），CPU 版 BGE 的检索吞吐此前实测约 13–16 QPS，这两个数字才是整条链路的真实瓶颈。

## 9. 国内网络注意事项

1. **Docker Hub 直连不通**：本机实测 `registry-1.docker.io` 超时，需在 `%USERPROFILE%\.docker\daemon.json` 配镜像加速：

```json
{ "registry-mirrors": ["https://docker.m.daocloud.io"] }
```

改完用 `docker desktop restart` 平滑重启引擎（改配置后必须重启才生效）。

2. **PyPI 源**：本机实测清华源不可达，容器内访问官方 `pypi.org` 正常，因此 `PIP_INDEX_URL` 默认留空。

3. **不要强制结束 Docker 进程**：会留下无法重命名的 AF_UNIX socket，导致下次启动失败。真遇到了就跑 `scripts\fix-docker-socket.ps1`（管理员权限），它会结束进程、移开卡住的运行时目录、恢复设置并重启引擎。

4. **容器里的前端是用户视图**：`web/.dockerignore` 刻意排除了 `.env`，所以镜像构建时不会把管理员 Key 内联进 JS（避免任何访客从产物里拿到 Key）。要在容器里演示管理员视图，构建时显式传入：

```powershell
docker compose build --build-arg VITE_ADMIN_API_KEY=<你的管理员 Key> web
```

（更稳妥的做法是保持镜像不含 Key，用本机 `npm run dev` 演示管理端，两者连的是同一个后端。）

## 10. 故障注入与恢复测试（2026-09-19 实测）

**应用层**（原生部署，杀进程）：故障前 200 / 146 ms → 杀后端 → **ConnectError 2126 ms 内快速失败** → 重启 → 5 秒内健康，请求恢复 200 / 1167 ms。

**容器层**（真实 Docker 部署，`docker stop` / `docker start`）：

| 阶段 | 观测结果 |
| --- | --- |
| 故障中 · 直连后端 | `ConnectError`，**2254 ms 快速失败**（没有挂死） |
| 故障中 · 前端页面 | **200 / 17 ms** —— 静态页面照常打开（优雅降级） |
| 故障中 · Nginx 反代后端 | **502**，3110 ms（上游不可用，网关如实报错） |
| 重启后端容器 | **5 秒内恢复 healthy**，请求恢复 200 / 970 ms |

结论：后端整体挂掉时，前端页面依然可用、调用方快速拿到错误而不是被拖死；容器重启后服务自动恢复，数据目录是宿主机 bind mount，不丢数据。

## 11. 尚未验证的部分（如实说明）

- 未验证容器在多实例/重启后的索引恢复（数据卷挂载已就位，但没有做过"重启电脑后再起容器并检索历史数据"的完整验证）。
- 未做高并发下的容器压测（并发压测是在原生部署上做的）。
