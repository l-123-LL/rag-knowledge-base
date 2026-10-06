# 交接文档（给接手的同事）

> **这份文档写给"人"**：目标是你在半小时内能把项目跑起来、看懂主干、知道改哪里、避开已知的坑。
> 仓库里另有两份面向不同读者的文档，别混：
>
> | 文档 | 写给谁 | 内容 |
> | --- | --- | --- |
> | `ONBOARDING.md`（本文件） | **接手的工程师** | 怎么跑、怎么改、坑在哪、现状与待办 |
> | `HANDOFF.md` | 接手项目的 AI 助手 | 目标、文件地图、技术决策、不可违反的约束 |
> | `PROGRESS.md` | 所有人 | 做到哪一步、实测数字、下一步计划（**每次开工先读**） |
>
> 本文件里的数字是 **2026-10-06 在这台机器上实测**的；凡是"未验证 / 文档声明 / 建议"我都会显式标注。

---

## 目录

1. [30 秒了解这个项目](#1-30-秒了解这个项目)
2. [五分钟跑起来](#2-五分钟跑起来)
3. [架构与一次提问的完整链路](#3-架构与一次提问的完整链路)
4. [代码地图：改什么看哪个文件](#4-代码地图改什么看哪个文件)
5. [数据存在哪里](#5-数据存在哪里)
6. [日常操作手册](#6-日常操作手册)
7. [配置项速查](#7-配置项速查)
8. [这台机器的特殊坑（否则你会怀疑人生）](#8-这台机器的特殊坑否则你会怀疑人生)
9. [已知问题与限制（诚实清单）](#9-已知问题与限制诚实清单)
10. [交接清单：账号、密钥、外部依赖](#10-交接清单账号密钥外部依赖)
11. [下一步建议](#11-下一步建议)

---

## 1. 30 秒了解这个项目

**它是什么**：一个企业智能客服系统。知识类问题走 RAG（检索 + 生成带引用的答案），业务类问题走工具调用（查订单、查物流、发起退款），答不出来或涉及敏感操作就转人工。每次执行都有可回放的轨迹，还有一套可复现的评测。

**它现在处于什么阶段**：**可演示、可评测、可继续开发，但业务数据是本地 mock，不能直接上生产。** 语料用的是 5 篇公开许可资料（不是某公司的真实资料）。

**已经做完的**（本机实测确认）：

| 能力 | 状态 | 证据 |
| --- | --- | --- |
| 资料导入（PDF / Word / Excel / CSV / HTML / MD） | 可用 | 后端 167 个测试；三种新格式已实测能被检索到 |
| 混合检索（BGE 向量 + BM25） | 可用 | 真实语料 20 条标注问题：doc_hit@1 0.95 / evidence_hit@1 0.90 |
| 生成 + 引用（DeepSeek） | 可用 | 回答带来源，引用可展开看原文 |
| 拒答 + 转人工（三条路径都有出口） | 可用 | 检索为空 / 分数不够 / 模型说没有，都会建工单 |
| 工具工作流 + 高风险审批 | 可用 | 5 个工具、组合调用、退款需人工批准且幂等 |
| 可观测（trace / metrics / 日志 / 脱敏） | 可用 | `/traces/{id}`、`/metrics`、`/alerts` |
| 评测体系（4 套 + 阈值标定 + 成本报告） | 可用 | 命令见第 6 节，全部可复现 |
| 部署（Docker / 本地脚本） | 可用但 Docker 在本机不稳 | 见第 8 节 |
| 代码托管与 CI | 可用 | https://github.com/l-123-LL/rag-knowledge-base ，7 次 CI 全绿 |

**明确没做的**：接真实订单/CRM/支付系统、坐席侧排队与实时会话、扫描版 PDF 的 OCR、公网部署与鉴权加固。

---

## 2. 五分钟跑起来

### 2.1 环境依赖

| 依赖 | 要求 | 本机现状（已验证） |
| --- | --- | --- |
| Python | 3.12 | `.venv` 已建好，位于仓库根目录 |
| Node.js | 20+ | 已装（前端用 Vite 5） |
| 模型权重 | `BAAI/bge-large-zh-v1.5` | 已缓存在 `models/huggingface/`（**不要删，重下很慢**） |
| DeepSeek API Key | 必须有才能生成 | 已配在 `backend/.env`（**不在 Git 里**） |
| Docker Desktop | 可选 | 装在 `D:\Docker`，但本机不稳定，见第 8 节 |

### 2.2 三种启动方式，按场景选

**方式 A：本地开发模式（推荐，改代码用这个）**

```powershell
cd D:\rag知识库
start-all.bat
```

会开三个窗口：

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 后端 | http://127.0.0.1:8000 | 接口文档 `/docs` |
| 管理端前端 | http://127.0.0.1:5173 | **有**资料管理、FAQ、审批面板、执行轨迹 |
| 用户端前端 | http://127.0.0.1:5174 | 客户视角，只有问答与转人工 |

管理端能不能看到管理功能，取决于 `web/.env` 里有没有 `VITE_ADMIN_API_KEY`（本机已配置）。

**方式 B：Docker 一键演示（给别人看用）**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

起容器 → 等健康检查 → 索引为空自动导语料 → 打开页面。
⚠️ **注意**：镜像默认**不内联管理员 Key**，所以 Docker 版的 5173 是**用户视图**，看不到审批面板。要在 Docker 里看管理端，得重新构建：`docker compose build --build-arg VITE_ADMIN_API_KEY=<你的Key> web`。

**方式 C：只跑后端（调接口/跑评测用）**

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2.3 首次启动的正常耗时（别误判成卡死）

| 阶段 | 正常耗时 | 说明 |
| --- | --- | --- |
| 后端启动 | 3–5 秒 | 只是接口就绪，**模型还没加载** |
| 第一次走 RAG 的请求 | **10–20 秒** | 首次要加载 BGE 模型（约 11 秒），之后每次检索 ~100 ms |
| 第一次 FAQ 请求 | < 100 ms | FAQ 不调模型、不检索 |

> 如果首次 RAG 请求卡到 60 秒以上：检查 `backend/.env` 里有没有 `HF_HUB_OFFLINE=1`。没有的话模型会去 HuggingFace 校验权重，网络受限时会退避重试很久——这个坑我踩过，已修（见第 8 节）。

### 2.4 五分钟验证清单（照着跑，对不上就说明环境有问题）

```powershell
# ① 后端健康
curl.exe http://127.0.0.1:8000/health
# 期望：{"status":"ok"}

# ② 语料规模
curl.exe http://127.0.0.1:8000/stats
# 期望：chunk_count = 74，source_count = 5

# ③ 后端测试 + 静态检查
cd backend
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider     # 期望 167 passed
..\.venv\Scripts\python.exe -m ruff check .                   # 期望 All checks passed!

# ④ 前端测试 + 类型检查
cd ..\web
npm test                                                      # 期望 31 passed
npm run typecheck                                             # 期望无输出（无错误）

# ⑤ 端到端问一句（会调用 DeepSeek，成本约 $0.0002）
curl.exe -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" ^
  -d "{\"question\":\"快递签收时可以先验收吗？\",\"top_k\":3}"
# 期望：status=done，回答里引用《快递暂行条例》第二十五条
```

**以上 5 条我 2026-10-06 全部实跑过**，数字与上面一致。

---

## 3. 架构与一次提问的完整链路

### 3.1 分层

```
前端（React + Vite + TS + Tailwind）
  └── 用户端 / 管理端，通过 /api 反代到后端
接口层（FastAPI，backend/app/main.py）
  └── /ask、/ask/stream、/ingest*、/faqs、/tickets、/approvals、/traces/{id}、/stats、/metrics、/alerts
编排层（两条链路）
  ├── RAG：pipeline.py → retrieval.py → generation.py
  └── 工具工作流：workflow.py → tools.py →（写操作）approvals.py
存储层
  ├── 向量库：vector_store.py（FAISS，落盘 backend/data/faiss）
  ├── 结构化：FAQ / 工单 / 审批 / 会话（都是 JSON 文件）
  └── 外部：DeepSeek API、mock 订单数据
横切能力
  └── 租户隔离、鉴权、限流、脱敏、日志、成本、备份
```

模块间的依赖关系图在 `docs/architecture-modules.png`（文字版 `docs/architecture-modules.md`）。

### 3.2 一次提问会经过什么（**理解项目看这一段就够**）

代码路径：`backend/app/main.py` 的 `/ask`

```
用户提问
 │
 ├─ ① 租户识别（请求头 X-Tenant-ID），可选鉴权（管理员 Key / OIDC）
 │
 ├─ ② 输入护栏：命中"忽略以上指令""输出系统提示词""访问其他租户"等 → 直接转人工，不进检索
 │
 ├─ ③ 规则意图：投诉 / 明确要求转人工 → 建工单 + 返回带工单号的话术
 │
 ├─ ④ FAQ 命中 → 零模型成本直接返回标准答案
 │     两道保护：问句含"定制/除外/生鲜"等例外语不短路；通用词（订单/客服）单独命中不算
 │
 ├─ ⑤ workflow_mode 分流：
 │      "tools" → 工具工作流状态机（最多 3 次业务工具调用，转人工不占预算，总超时 15 秒）
 │      "rag"（默认）→ 走下面
 │
 └─ ⑥ RAG 主链路：
        构建检索词（追问时把上一轮问题拼进来）
        → 混合检索：BGE 向量 + BM25，min-max 归一化后按 0.7 / 0.3 融合
        → 元数据过滤：租户、停用来源、生效时间窗口、同 doc_key 只留最高版本
        → 阈值判定：最高原始余弦 < RAG_MIN_SCORE(0.37) → 判"资料不足"
        → 命中子块时扩展到父块上下文（父子切分开启时）
        → DeepSeek 生成（支持 SSE 流式）
        → 生成后识别"模型级拒答" → 补一句带工单号的转人工
 │
 └─ 记录会话记忆 + 写结构化日志（路由/模型/延迟/token/成本/引用数）
    返回 { answer, citations, model, status, latency_ms, usage, cost, trace_id }
```

**三条"答不出来"的路径全都有出口**：检索为空、相似度低于阈值、模型自己说"资料里没有"——都会建工单并返回带工单号的话术。这是这个项目区别于玩具 demo 的关键设计。

### 3.3 默认值与开关（容易记混的几个）

| 项 | 默认 | 怎么改 |
| --- | --- | --- |
| 工作流模式 | `rag` | 请求体传 `workflow_mode="tools"`，或前端顶部切换 |
| 混合检索权重 | 向量 0.7 / BM25 0.3 | `HybridRetriever(dense_weight=...)` |
| 拒答阈值 | `RAG_MIN_SCORE=0.37` | `backend/.env`，**换语料必须重标** |
| 父子切分 | 关闭 | `HIERARCHICAL_CHUNKING=true` |
| 重排 rerank | **关闭** | `RERANK_MODEL=...`；注意实测是负收益，见第 9 节 |
| top-k | 5 | `/ask` 请求体的 `top_k` |

---

## 4. 代码地图：改什么看哪个文件

后端 30 个模块（约 3800 行），按职责分组：

| 想改什么 | 看这个文件 | 行数 |
| --- | --- | --- |
| 加接口 / 改请求响应 | `backend/app/main.py`（入口）、`schemas.py`（模型） | 888 / 77 |
| 切分规则、块大小 | `backend/app/chunking.py` | 70 |
| 换嵌入模型 | `backend/app/embeddings.py` | 48 |
| 换向量库（比如 pgvector） | `backend/app/vector_store.py`（实现 `VectorStore` 接口即可） | 180 |
| 检索融合、阈值、版本过滤 | `backend/app/retrieval.py` | 221 |
| 引用格式、父子上下文 | `backend/app/pipeline.py` | 140 |
| 资料解析（PDF/Word/Excel…） | `backend/app/ingestion.py` | 175 |
| 提示词、模型参数、流式 | `backend/app/generation.py` | 132 |
| 追问指代 | `backend/app/followup.py` | 58 |
| 拒答识别 | `backend/app/refusal.py` | 31 |
| 工具定义与超时重试 | `backend/app/tools.py` | 338 |
| 工作流状态机、路由规则 | `backend/app/workflow.py` | 429 |
| 审批单与幂等 | `backend/app/approvals.py` | 88 |
| FAQ 存储与命中规则 | `backend/app/faq_store.py` | 227 |
| 日志、指标、脱敏 | `backend/app/observability.py`、`trace_store.py` | 105 / 72 |
| 依赖注入（组装各组件） | `backend/app/factory.py` | 25 |

前端主要文件（`web/src/`，另有 `components/ErrorBoundary.tsx` 兜底与 `components/icons.tsx` 图标）：

| 文件 | 作用 |
| --- | --- |
| `App.tsx` | 页面骨架与状态，模式切换、Trace 入口、审批接线 |
| `components/ChatPanel.tsx` | 对话区 + 空状态引导 |
| `components/AnswerCard.tsx` | 单条问答卡片（含加载骨架屏、拒答样式） |
| `components/AnswerBody.tsx` | 轻量 Markdown 渲染（加粗 / 列表 / 行内代码） |
| `components/CitationList.tsx` | 引用列表，默认展开第一条 |
| `components/QuestionInput.tsx` | 输入区 + 转人工按钮 |
| `components/SourcePanel.tsx` | 左侧资料列表、统计指标、管理操作 |
| `components/TraceTimeline.tsx` | 执行轨迹面板 |
| `components/ApprovalPanel.tsx` | 高风险操作审批面板 |

设计令牌（颜色、字号、圆角、阴影）在 `web/tailwind.config.js` 与 `web/src/index.css`。

---

## 5. 数据存在哪里

| 数据 | 位置 | 格式 | 能不能删 |
| --- | --- | --- | --- |
| 向量索引 + 分块元数据 | `backend/data/faiss/` | `index.faiss` + `records.json` | 可以删，但要重新导入语料（`scripts/ingest-corpus.ps1`） |
| 语料原文 | `backend/corpus/` | Markdown（**进 Git**） | 不要删，语料源头 |
| 待导入的企业资料 | `backend/data/incoming/` | 任意支持格式 | 可以删（导入后就进索引了） |
| 问答日志 | `backend/data/logs/ask.jsonl` | 每行一条 JSON | 可以删（`/metrics` 会归零） |
| 执行轨迹 | `backend/data/traces/` | 按天 JSONL | 可以删 |
| 审批单 | `backend/data/approvals/{租户}/` | JSON | **不要随意删**，是审计记录 |
| 工单 | `backend/data/tickets/` | JSON | 同上 |
| FAQ | `backend/data/faqs/{租户}.json` | JSON | 备份后再改 |
| 会话记忆 | `backend/data/sessions/` | JSON | 可以删 |
| mock 订单/物流 | `backend/mock/orders.json` | JSON（**进 Git**） | 不要删，工具层依赖它 |
| 模型权重 | `models/huggingface/` | HF 缓存 | **不要删**，重新下载很慢 |

除 `backend/corpus/` 和 `backend/mock/` 外，其余都在 `.gitignore` 里 —— **不会进仓库**。

---

## 6. 日常操作手册

### 6.1 导入资料

```powershell
# 把文件放进 backend/data/incoming/（支持 .md/.txt/.html/.csv/.xlsx/.docx/.pdf）
.\.venv\Scripts\python.exe scripts\ingest_folder.py
# 只看会导哪些、不真的导：
.\.venv\Scripts\python.exe scripts\ingest_folder.py --dry-run
```

单文件失败不会中断整批；重复导入会按内容哈希**幂等跳过**。

### 6.2 ⚠️ 换语料后必须重标阈值（最容易漏的一步）

**不做的后果**：明明有资料，却因为相似度低于旧阈值被判"资料不足"转人工。

```powershell
# 1) 先改 backend/evaluation/corpus_questions.json：域内 10 条 + 域外 8 条业务问题
# 2) 重新标定
cd backend
..\.venv\Scripts\python.exe -m evaluation.calibrate_threshold
# 3) 把输出的推荐值写进 backend/.env 的 RAG_MIN_SCORE，然后重启后端
```

脚本在两组分数重叠时会**直接报"分不开"**，不会给一个假的安全值——那种情况要调整语料或问题集。

### 6.3 跑测试与检查（改代码前后都该跑）

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest          # 167 个用例
..\.venv\Scripts\python.exe -m ruff check .    # 静态检查

cd ..\web
npm test && npm run typecheck && npm run build
```

> 项目规矩（见 `AGENTS.md`）：**每次改动都要有一个 Git commit，且交付前所有测试必须通过。**

### 6.4 评测（验证效果、产出可对外引用的数字）

```powershell
cd backend
..\.venv\Scripts\python.exe -m evaluation.corpus_eval          # 真实语料检索：doc_hit / evidence_hit / MRR
..\.venv\Scripts\python.exe -m evaluation.enterprise_eval      # 50 条客服问题集
..\.venv\Scripts\python.exe -m evaluation.agent_eval --tag full --use-real-embedder --offline   # 150 条 Agent 任务
..\.venv\Scripts\python.exe -m evaluation.cost_report          # 从日志算单次成本
..\.venv\Scripts\python.exe -m evaluation.calibrate_threshold  # 阈值标定
..\.venv\Scripts\python.exe -m evaluation.load_test --url http://127.0.0.1:8000 --concurrency 1,10,20 --requests 40
```

前三条要加载模型（第一次约 11 秒）；报告落在 `backend/evaluation/reports/`。

### 6.5 排障：先看这三样

```powershell
# ① 健康与规模
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/stats

# ② 运行指标（累计问答、平均延迟、有帮助率、成本）
curl.exe http://127.0.0.1:8000/metrics

# ③ 最近 5 条问答日志（含路由、模型、延迟、token、成本）
Get-Content backend\data\logs\ask.jsonl -Tail 5
```

某一次具体执行有什么问题，用返回的 `trace_id` 查：`GET /traces/{trace_id}`，或前端顶部「执行轨迹」面板。

### 6.6 备份与恢复

```powershell
# 后端自带的打包备份
curl.exe -X POST http://127.0.0.1:8000/backup
# 产物在 backend/data/backups/ 下
```

Git 仓库本身就是代码的备份；本地还留了一份全量 bundle：`backups/rag-knowledge-base-YYYYMMDD.bundle`（含全部提交历史，可在任意机器 `git clone` 还原）。

---

## 7. 配置项速查

都在 `backend/.env`（本机已配置，**不在 Git 里**；模板见 `backend/.env.example`）。

| 变量 | 当前值 | 作用 | 什么时候改 |
| --- | --- | --- | --- |
| `DEEPSEEK_API_KEY` | 已配置 | 生成模型的 Key | 换 Key / 换人维护时 |
| `ADMIN_API_KEY` | 已配置 | 管理端与写接口的鉴权 | 轮换密钥时（前端 `web/.env` 里也要同步） |
| `RAG_MIN_SCORE` | `0.37` | 拒答阈值（原始余弦） | **换语料后必须重标** |
| `HF_HOME` | `models/huggingface` | 模型权重缓存目录 | 一般不动 |
| `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` | `1` | 离线加载，避免首次请求卡几十秒 | 要下载新模型时临时注释掉 |
| `HIERARCHICAL_CHUNKING` | 未设置（=关闭） | 父子切分 | 长文档答不完整时开启 |
| `RERANK_MODEL` | 未设置（=关闭） | 重排模型 | 见第 9 节，当前实测负收益 |
| `OCR_ENABLED` | 未设置（=关闭） | 扫描版 PDF 的 OCR 钩子 | 未实测，谨慎开启 |
| `TOOL_TIMEOUT_SECONDS` | 默认 3 | 单个工具超时 | 接真实系统变慢时 |
| `WORKFLOW_TOTAL_TIMEOUT_SECONDS` | 默认 15 | 工作流总超时 | 同上 |
| `RATE_LIMIT_PER_MINUTE` | 默认 120 | 每 IP 每分钟请求上限 | 压测时用 `docker-compose.loadtest.yml` 关掉 |

前端另有 `web/.env`：`VITE_ADMIN_API_KEY` 决定 5173 是管理视图还是用户视图。

---

## 8. 这台机器的特殊坑（否则你会怀疑人生）

这一节都是**真实踩过并记录**的问题，换机器不一定复现，但在这台机器上一定会遇到。

### 8.1 Docker Desktop 启动失败：socket 卡死

**症状**：启动时弹窗报

```
starting services: initializing Ingest server: listening on unix:///C:/Users/86138/AppData/Local/Docker/run/sailor-ingest.sock:
rename ...sailor-ingest.sock ...sailor-ingest.sock.stale: The file cannot be accessed by the system.
```

**原因**：Docker Desktop 非正常退出（崩溃、强杀进程、直接重启电脑）后残留的 AF_UNIX socket 无法改名或删除，每次启动都卡在同一步。

**修复**：项目里已经写好脚本，**需要管理员权限**：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fix-docker-socket.ps1
```

它做四件事：结束 Docker/WSL 进程 → 把 `%LOCALAPPDATA%\Docker` 和 `docker-secrets-engine` 整体改名移开（**不删除**）→ 恢复设置文件 → 重启并等待引擎就绪（最多 5 分钟）。

> **2026-09-24 实测补充**：这次启动时 Docker 后端进程 23 秒后自己崩了（日志里只有 `backend process exited` 和错误对话框，没有明确原因）。考虑到这台机器 Docker 的不稳定程度，**日常开发建议直接用 `start-all.bat`（本地模式），不要依赖 Docker**；Docker 只在需要给别人演示或验证部署时才用。

### 8.2 网络：GitHub 直连不通

**事实**：这台机器直连 `github.com:443` / `ssh.github.com:443` / `codeload.github.com` 都是超时；本机有代理客户端（`YunNiaoLoonCore`，监听 `127.0.0.1:17890`）。

**影响**：

- `git push` 需要代理生效（代理客户端开"系统代理/TUN"模式，或给 git 单独指定：`git -c http.proxy=http://127.0.0.1:17890 push`）
- 代理会间歇性抖动：同一分钟里可能一次 200、下一次超时。**推送失败先重试，不要以为配置坏了**
- 浏览器里访问 GitHub 也可能被代理规则或插件拦（实测出现过 `ERR_BLOCKED_BY_CLIENT`），那时换手机或改规则

**凭据现状**：git 凭据已存在 Windows 凭据管理器里（`git:https://github.com`），所以 `git push` 不需要每次输令牌。⚠️ 但当前用的令牌是**经典 PAT，勾了 `repo` + `workflow`**：仓库里有 `.github/workflows/ci.yml`，**没有 `workflow` 权限的令牌会让整次推送被拒**（报错在最后一行，容易看漏）。

### 8.3 HuggingFace 校验导致首次请求卡几十秒

**症状**：本地启动后端后，第一次走 RAG 的请求 60 秒都没返回，日志里只有 FAQ 的记录。

**原因**：本地启动没有设离线标志，`SentenceTransformer` 去 HuggingFace 校验权重；网络受限时退避重试很久（Docker 那套在 compose 里设了，只有本地漏了）。

**已修**：`backend/.env` 里加了 `HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1`。
**要下载新模型时**：临时注释掉这两行，下载完再打开。

### 8.4 Windows PowerShell 5.1 的两个坑

如果你在改脚本会遇到：

1. **中文脚本必须存成带 BOM 的 UTF-8**，否则 5.1 会把中文按 GBK 读，报一堆语法错误。项目里的 `.ps1` 都是带 BOM 的。
2. **`Invoke-RestMethod -Form` 是 PowerShell 6+ 才有的**，5.1 不支持 multipart 上传。所以批量导入脚本用的是 Python（`scripts/ingest_folder.py`），不要改回 PowerShell。

### 8.5 不要提交的东西

`.gitignore` 已覆盖：`.venv/`、`data/`、`models/`、`backups/`、`.env`、`backend/.env`、`*.log`、`.github-token`。

另外**个人材料**（面试准备稿、投递记录、学习手册）也加进了忽略规则。⚠️ **提醒**：`INTERVIEW.md`、`docs/BOSS*`、`docs/AI_Agent*`、`docs/Day?_*`、`docs/模拟面试*` 这些文件**物理上就在仓库目录里**，只是被忽略。更稳妥的做法是把它们移到仓库目录之外（例如 `D:\求职材料\`）——`.gitignore` 防的是误操作，物理隔离才是真安全。

---

## 9. 已知问题与限制（诚实清单）

按"严重程度 × 是否已修"排列，明确区分状态。

| # | 问题 | 状态 | 影响与建议 |
| --- | --- | --- | --- |
| 1 | 语料是**公开替代资料**，不是企业真实资料 | 未解决（需要资料） | 指标只代表这批语料；换成真实资料后**必须重标阈值** |
| 2 | 阈值分离间隙窄（域内 0.377 / 域外 0.360，只差 0.017） | 已知 | 语料再变就可能重叠；标定脚本会报"分不开"，届时要调语料或问题集 |
| 3 | **rerank 实测为负收益**（doc_hit@1 0.95→0.85，6.5 s/次） | 已决策：默认关闭 | 这是**当前语料规模**的结论，不是"重排没用"；语料变大后应复测 |
| 4 | 业务数据全是**本地 mock**（20 订单 + 10 物流） | 未解决（需要对接） | 工具层的"执行"只建本地单，不动真实资金 |
| 5 | **转人工只到"建工单 + 话术"** | 未实现 | 没有坐席排队、分配、实时会话、消息回流 |
| 6 | **OCR 未实测**（只有钩子） | 未验证 | 扫描版 PDF 请先自行 OCR 成 Word/文本 |
| 7 | 默认**无鉴权**（未配 Key 时只打印警告） | 已知 | **公网部署前必须补**，否则 `/ingest`、`/approvals` 是裸的 |
| 8 | 评测集是**自建的 70 条** | 已知 | 不是业务方标注的真实分布；上线前应用真实工单采样重建 |
| 9 | Docker 在本机不稳定 | 环境问题 | 见 8.1；日常用本地模式 |
| 10 | 前端没有 ESLint/Prettier（后端有 ruff） | 未做 | 不影响运行，属于锦上添花 |

**已经修好、不用再操心的**（都带回归测试）：分块 id 撞车导致的检索分数错位、FAQ 吞掉例外条款、模型级拒答没有转人工出口、BM25 的 O(N²) 热点、中文路径下 FAISS 写索引失败、nginx 缓存后端 IP 导致前端静默回退 mock、本地启动的离线加载。

---

## 10. 交接清单：账号、密钥、外部依赖

### 10.1 密钥与账号（**本文件不写任何密钥值**）

| 项 | 存在哪里 | 谁需要知道 | 备注 |
| --- | --- | --- | --- |
| DeepSeek API Key | `backend/.env` 的 `DEEPSEEK_API_KEY` | 后端维护者 | 计费账号，注意余额；单次问答约 $0.0002 |
| 管理端 Key | `backend/.env` 的 `ADMIN_API_KEY` + `web/.env` 的 `VITE_ADMIN_API_KEY`（两处要一致） | 管理员 | 轮换时两处同时改 |
| GitHub 仓库 | https://github.com/l-123-LL/rag-knowledge-base | 需要能 push 的人 | 账号 `l-123-LL`；git 凭据在本机 Windows 凭据管理器 |
| GitHub 令牌 | Windows 凭据管理器（`git:https://github.com`） | 需要能 push 的人 | 经典 PAT，需要 `repo` + `workflow` 两个权限 |
| Docker Hub | 只用公开镜像 | — | 本机配了国内镜像加速 |

### 10.2 接手时需要确认的事项

1. **要不要保留 GitHub 上的公开可见性**（目前是 public，代码里没有任何密钥，但包含完整实现）
2. **真实资料的来源与范围**：接哪个业务线、资料从哪取、有没有客户隐私需要脱敏
3. **是否要上线**：决定鉴权、限流、备份要不要从"可选"变成"必选"
4. **成本与延迟的目标线**：现在的口径是单次 $0.000247、检索 ~100 ms、首 token 2.5–3 s，需要定一个验收标准
5. **是否继续维护这台开发机**（Docker 不稳定 + 需要代理才能访问 GitHub）

---

## 11. 下一步建议

按"投入产出比"排序，前两项必须用真实资料才能推进：

| 优先级 | 事项 | 具体做什么 | 涉及文件 |
| --- | --- | --- | --- |
| P0 | **接入真实资料** | 资料放进 `backend/data/incoming/` → `scripts/ingest_folder.py` → 重标阈值 → 重跑三套评测 | `scripts/ingest_folder.py`、`evaluation/corpus_questions.json`、`backend/.env` |
| P0 | **重标阈值并验证** | 按 `docs/INGEST-ENTERPRISE-DATA.md` 的五步走一遍 | `evaluation/calibrate_threshold.py` |
| P1 | 对接真实业务系统 | 把 `order_store.py` 的 mock 换成真实订单/CRM 接口，保留工具层的超时与降级 | `backend/app/order_store.py`、`tools.py` |
| P1 | 坐席侧打通 | 转人工后的排队、分配、消息回流；现在只有工单落盘 + 可选 Webhook | `ticket_store.py`、`main.py` |
| P2 | 公网部署加固 | 鉴权（OIDC）、HTTPS、限额、备份策略、监控接入 | `security.py`、`docs/DEPLOYMENT.md` |
| P2 | 扩充评测集 | 从业务工单里采样，把 70 条扩到几百条 | `backend/evaluation/` |
| P3 | 前端工程化 | 加 ESLint + Prettier；跨浏览器自动化回归 | `web/` |

---

## 附：文档索引

| 想知道什么 | 看哪份 |
| --- | --- |
| 怎么跑、改哪里、坑在哪 | **本文件** |
| 项目目标、文件地图、技术决策、不可违反的约束 | `HANDOFF.md` |
| 做到哪一步、实测数字、下一步 | `PROGRESS.md` |
| RAG 每个参数的选型理由与实测数字 | `docs/RAG_DESIGN.md` |
| 接入企业自有资料的全流程 | `docs/INGEST-ENTERPRISE-DATA.md` |
| 部署、验证清单、回滚、故障排查 | `docs/DEPLOYMENT.md` |
| 9 个真实故障的排查过程 | `docs/FAILURE-CASES.md` |
| 3–5 分钟演示怎么讲 | `docs/DEMO-SCRIPT.md`、`docs/VIDEO-SCRIPT.md` |
| 发布到 GitHub 的完整步骤与踩坑 | `docs/PUBLISH-TO-GITHUB.md` |
| 模块依赖图 | `docs/architecture-modules.png` |
