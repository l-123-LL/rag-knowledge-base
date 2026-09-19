# 项目交接文档

> 目标：新的 AI 只读 `AGENTS.md` + `HANDOFF.md` + `PROGRESS.md` 就能接手，不依赖任何聊天记录。
> 分工：本文件写**稳定内容**（目标、架构、文件地图、决策、约束、运行方式）；**会变的内容**（做到哪、数字、下一步）写在 `PROGRESS.md`，开工前先读它。
> 最后更新：2026-09-19。未实现的内容一律标注「计划」。

---

## 1. 项目目标

### 做什么

面向企业的智能客服系统，同时具备两条链路：

- **RAG 链路（默认）**：从产品手册、FAQ、售后与物流政策中混合检索，用 DeepSeek 生成带引用的回答。
- **工具工作流（可选）**：`workflow_mode="tools"` 时走「规则路由 → 工具调用 → 质量判断 → 回答 / 转人工」，支持订单查询、物流轨迹、退款申请（需审批）。

共同要求：FAQ 精确命中优先；检索不到就拒答并转人工；高风险写操作必须审批；每次执行可追踪；指标可复现。

### 给谁用

- 企业客户：网页自助提问（用户视图，只有问答与转人工）。
- 客服与运营：维护资料、FAQ，处理审批与工单（管理员视图）。
- 当前实际使用者：项目作者，用于验证流程与产出面试材料。

### 成功标准

- 一条命令起全栈（`docker compose up --build` 或 `start-all.bat`）。
- 有 150 条可复现评测集，覆盖 FAQ / 订单 / 物流 / 政策 / 多轮 / 转人工 / 拒答与注入。
- 每次任务能用 `trace_id` 还原：路由、工具、重试、token、成本、最终结果。
- 副作用操作有权限、dry-run、幂等与人工审批。
- 所有对外引用的数字都能在仓库里复现。

### 方向变更

项目最初是「医学知识库 RAG」，中途整体转向**企业智能客服**；后续又从纯 RAG 扩展出**可选工具工作流 + 审批**。医学阶段的残留（示例数据集、包 docstring、测试里的示例文本）已于 2026-09-19 全部替换为客服语义，仓库内不再有医学内容。

---

## 2. 当前进度

**详细进度与实测数字看 `PROGRESS.md`。** 这里只给结论：RAG 闭环 + 可选工具工作流 + 审批 + 评测 + 可观测 + Docker 部署均已实现并实机验证；测试 119（后端）/ 25（前端）；Agent 评测 150 条、任务成功率 99.33%。剩余是需要外部条件的收尾（导入真实资料、CI 推远程）。

---

## 3. 文件地图

### 根目录

- `AGENTS.md`：强制规则（每改动一个 commit、测试必须通过、新会话先读文档）。
- `PROGRESS.md`：当前进度、实测数字、下一步计划（**每次开工先读**）。
- `HANDOFF.md`：本文件。
- `INTERVIEW.md`：面试材料（陈述、问答、数字口径、失败案例）。
- `README.md`：项目说明与快速开始。
- `docker-compose.yml` / `docker-compose.loadtest.yml`：部署编排 / 压测覆盖（关限流）。
- `start-all.bat`、`start-backend.bat`、`start-admin-web.bat`、`start-user-web.bat`：一键启动脚本。
- `.vscode/tasks.json`：VS Code 任务（等价于上面的脚本）。
- `.gitignore`：忽略 `.venv/`、`data/`、`models/`、`backups/`、`.env`、`backend/.env`、`.pytest-*`。

### 后端 · 接口与配置

- `backend/app/main.py`：FastAPI 入口，20+ 接口（`/ask`、`/ask/stream`、`/ingest*`、`/faqs`、`/tickets`、`/approvals`、`/traces/{id}`、`/stats`、`/metrics`、`/alerts`、`/backup` 等）。
- `backend/app/schemas.py`：Pydantic 请求/响应模型（`AskRequest.workflow_mode`、`AskResponse.trace_id/steps`、`ApprovalDecisionRequest`）。
- `backend/app/config.py`：加载 `backend/.env`。
- `backend/app/factory.py`：依赖注入工厂，组装嵌入 / 向量库 / 检索 / 重排 / 生成。
- `backend/.env.example`：环境变量清单（含单价、工具超时、审批目录、父子切分开关）。
- `backend/Dockerfile`：非 root 运行、CPU 版 torch、`COPY mock`、HEALTHCHECK。

### 后端 · RAG 核心

- `backend/app/chunking.py`：归一化、段落切分、窗口切分，以及 `split_text_hierarchical`（父块 1200 / 子块 400 / 重叠 80）。
- `backend/app/embeddings.py`：`Embedder` 接口、`HashEmbedder`（测试替身）、`SentenceTransformerEmbedder`（`BAAI/bge-large-zh-v1.5`）。
- `backend/app/vector_store.py`：`VectorStore` 接口、内存实现、`FAISSVectorStore`（`IndexIDMap2 + IndexFlatIP`，索引与元数据分开落盘）。
- `backend/app/retrieval.py`：jieba 分词、`BM25Index`（含一次性批量打分 `scores()`）、`HybridRetriever`（min-max 归一化 + 0.7/0.3 融合；按 `doc_key` 只保留最高版本、按 `effective_from/to` 过滤生效窗口）、`RetrievedChunk`（含 `raw_dense_score`）。
- `backend/app/reranker.py`：可选 BGE 重排（`RERANK_MODEL` 开关）。
- `backend/app/generation.py`：DeepSeek 客户端（普通 + 流式）、`GenerationResult`。
- `backend/app/pipeline.py`：`RAGPipeline`（检索 → 阈值判定 → 父块上下文扩展 → 生成），`ingest_text` 支持父子切分。
- `backend/app/ingestion.py`：TXT / Markdown / HTML / 文本层 PDF（表格转 Markdown）/ 网页正文。

### 后端 · 工具与工作流

- `backend/app/tools.py`：工具注册表 + 5 个工具（`knowledge_search` / `order_lookup` / `logistics_track` / `human_handoff` / `refund_request`），Pydantic 输入输出、统一错误码、超时（默认 3 s）、重试（默认 1 次）、dry-run、`requires_approval`。
- `backend/app/workflow.py`：最小状态机（输入护栏 → 规则意图 → 退款审批 → 订单/物流工具 → 工具组合 → FAQ → 知识检索 → 转人工），多轮订单号指代（`reuse_order_id_from_history`），最多 3 次业务工具调用（转人工不占预算）、总超时 15 s。
- `backend/app/approvals.py`：审批单持久化（`data/approvals/{tenant}/`）、幂等键（租户+工具+参数）、`create/get/list/save/count_pending`。
- `backend/app/trace_store.py`：`trace_id` 生成、按天 JSONL 写入、按 id 回读、PII 脱敏（手机号/邮箱/证件号/Key）。
- `backend/app/order_store.py`：读取本地 mock 订单与物流（`backend/mock/orders.json`，20 订单 + 10 物流），租户过滤与手机号脱敏。

### 后端 · 业务与运维

- `backend/app/faq_store.py`：FAQ 持久化、关键词命中、增删改与版本号。
- `backend/app/intent.py`：规则意图（投诉 / 明确转人工 / 否定词防误判）。
- `backend/app/ticket_store.py`：工单落盘与可选 Webhook 外发。
- `backend/app/session_store.py`：会话记忆（最近 8 条）。
- `backend/app/tenant.py`：`X-Tenant-ID` 租户识别。
- `backend/app/security.py`：可选管理员 Key、可选 OIDC/JWT 校验。
- `backend/app/observability.py`：JSONL 日志读写与聚合（容忍损坏半行）、可选监控 Webhook。
- `backend/app/cost.py`：按配置单价估算单次成本。
- `backend/app/backup.py`：数据目录打包备份。

### 后端 · 评测与测试

- `backend/evaluation/enterprise_eval.py`：50 条检索评测集 + CLI（`--embedder bge|hash`、`--offline`）。
- `backend/evaluation/run_eval.py`：样例语料检索评测 CLI。
- `backend/evaluation/calibrate_threshold.py` + `corpus_questions.json`：**拒答阈值标定**——读 `backend/corpus/` 的真实语料，算域内问题最低分与域外问题最高分，给出建议阈值与「保留/挡下」数量；两组重叠时会直接报"分不开"，不给假的安全值。
- `backend/evaluation/corpus_eval.py` + `corpus_eval_questions.json`：**真实语料检索评测**（20 条标注问题：期望文档 + 证据关键词），区分 `doc_hit@k`（文档对不对）与 `evidence_hit@k`（证据句有没有命中），报告写到 `reports/corpus-eval-*.md`。当前基线 doc_hit@1 0.95 / evidence_hit@1 0.90 / evidence_mrr 0.925。
- `backend/evaluation/agent_tasks.json`：100 条 Agent 任务（订单 25 / 物流 15 / 政策 15 / 多轮 20 / 转人工 13 / 拒答与注入 12）。
- `backend/evaluation/agent_eval.py`：Agent 评测（默认确定性生成器、`--use-real-model`、`--tag smoke|core|full`、`--limit`、`--offline`），输出 JSON + Markdown。
- `backend/evaluation/load_test.py`：并发压测（混合问题、并发级别、P50/P95/P99、吞吐、状态码分布）。
- `backend/evaluation/generation_eval.py` + `backend/app/judge.py`：生成质量（faithfulness / relevance）打分器与批量评估。
- `backend/evaluation/reports/`：评测与压测报告留档。
- `backend/tests/`：23 个测试文件、119 个用例。
- `backend/mock/orders.json`：本地模拟订单与物流（**不要放 `data/`，那里被 gitignore**）。

### 前端 `web/`

- `web/src/App.tsx`：页面骨架与状态；RAG / 工具工作流切换、Trace 入口、管理员审批面板接线。
- `web/src/api/client.ts`：API 抽象层（`/api` 代理、租户头、可选管理员 Key、mock 回退），含 `getTrace` / `listApprovals` / `decideApproval`。
- `web/src/components/AnswerCard.tsx`、`CitationList.tsx`、`ChatPanel.tsx`、`QuestionInput.tsx`、`SourcePanel.tsx`：问答、引用、输入、来源与统计。
- `web/src/components/TraceTimeline.tsx`：执行轨迹面板（步骤、工具、重试、耗时、token、成本、转人工原因）。
- `web/src/components/ApprovalPanel.tsx`：高风险操作审批面板（dry-run 预览 + 批准/驳回）。
- `web/src/components/ErrorBoundary.tsx`、`icons.tsx`：兜底与图标。
- `web/.env`（未提交）：`VITE_ADMIN_API_KEY` 决定管理端；`web/.env.user`：用户视图模式（Key 置空）。
- `web/Dockerfile` / `nginx.conf`：镜像与反代；镜像默认**不含**管理员 Key（用户视图），需要管理端时用 `--build-arg VITE_ADMIN_API_KEY=xxx`。

### 文档与脚本

- `docs/architecture-modules.svg|png|md`：模块划分图。
- `docs/DEPLOYMENT.md`：部署、验证清单、回滚、备份恢复、故障排查、并发压测、国内网络注意事项。
- `docs/CASE-STUDY.md`：一页项目案例。
- `docs/RAG_DESIGN.md`：**RAG 设计说明**——数据、切分、Embedding、向量库、检索、Prompt、评估、工程、数字汇总与已知不足。对外讲技术选型、面试被追问参数时看这份，所有数字都标注了口径和复现命令。
- `docs/FAILURE-CASES.md`：七个真实故障与排查记录。
- `docs/DEMO-SCRIPT.md`：3–5 分钟演示脚本。
- `docs/PHASE0-最小改动方案.md`：本轮改造方案（已执行完）。
- `scripts/fix-docker-socket.ps1`：Docker Desktop 启动失败修复脚本（管理员权限运行；脚本必须存为**带 BOM 的 UTF-8**，否则 PowerShell 5.1 会把中文按 GBK 读导致语法错误）。
- `scripts/ingest-corpus.ps1`：把 `backend/corpus/` 的语料逐篇导入运行中的后端（从 `backend/.env` 读 `ADMIN_API_KEY`，不打印、不落日志）。注意两个 Windows 细节：脚本必须存为**带 BOM 的 UTF-8**；请求体必须显式转成 UTF-8 字节，否则 PowerShell 5.1 会按本地代码页编码，中文正文被后端按 UTF-8 解码失败。幂等，重复执行只跳过已存在的分块。
- `backend/corpus/`：演示语料（5 篇公开资料 + `README.md` 说明来源与许可）。README 不入库。

---

## 4. 关键决策及原因

1. **工具工作流做成可选模式**（`workflow_mode`，默认 `rag`）：既有链路与测试不受影响，出问题一个参数回退。
2. **规则先于模型**：投诉、明确转人工、输入护栏在规则层短路，不进检索与生成；FAQ 命中零模型成本。
3. **Agent 状态机自写，不引 LangGraph**：只做单跳任务，自写约 360 行可控、可测；LangGraph 仅作设计参考。
4. **工具分级**：低风险写操作（本地建单）即时执行；高风险（退款）必须 dry-run + 人工审批，幂等键防止重复执行。
5. **阈值用原始余弦相似度**：归一化分数永远有最大值 1.0，做不了绝对判断。当前语料（5 篇公开资料 / 74 分块）标定 `RAG_MIN_SCORE=0.37`：域内 10/10 保留、域外 8/8 挡下（域内最低 0.377 vs 域外最高 0.360）。标定脚本 `backend/evaluation/calibrate_threshold.py` 可复现；上一轮示例语料上的取值是 0.42。
5.1 **分块 id 必须全局唯一**：id 用「来源-序号-内容 sha1 前 8 位」。历史实现是 `text-{index}`，多篇资料导入时 id 撞车，检索层按 id 回填分数会互相覆盖（详见 `docs/FAILURE-CASES.md` 案例八）。检索层现已改为按向量库内部下标对齐，属于同一类 bug 的第二道防线。
6. **父子切分**：子块（400 字）检索、父块（1200 字）生成，避免答案被切分边界截断；父块文本存在子块 metadata 里，代价是索引体积变大。
7. **BM25 一次打分**：原实现逐文档重算全量分数（O(N²)），改为 `scores()` 一次算完；512 条索引检索从 370.9 ms 降到 187.5 ms。
8. **评测分两套**：检索质量用真实 BGE 单独评测；Agent 任务指标用确定性生成器（零 API 花费、可高频回归），生成质量交给 `judge.py` 抽样。
9. **评测集 150 条**：100 条手写 Agent 任务 + 50 条知识问答（复用 `enterprise_eval` 语料，单一数据源）。
10. **Docker 用 CPU 版 torch**：Linux 上装 `sentence-transformers` 默认拉 CUDA 版 torch（nvidia-* 数 GB），改用 `download.pytorch.org/whl/cpu` 后镜像 2.27 GB。
11. **镜像不内联管理员 Key**：`web/.dockerignore` 排除 `.env`，默认构建出用户视图；需要管理端时显式 `--build-arg`。
12. **日志读取容错**：追加写日志可能被强杀截断，聚合逻辑跳过损坏行（否则 `/metrics`、`/alerts` 会整个 500）。
13. **知识带版本与生效时间**：同一 `doc_key` 只召回最高版本，`as_of` 可按历史日期检索当时生效的政策——客服场景里"政策改过，用户问的是当时的规定"必须能答对，也避免新旧政策同时命中。
14. **工具组合的做法**：同时提到订单与物流时，先 `order_lookup` 拿状态、再 `logistics_track` 拿轨迹，合成一条答案；评测里把"期望工具"判定改成"出现在成功调用的工具集合中"，否则组合路径会被误判成路由错误。
15. **FAQ 短路要留例外出口**：FAQ 是关键词命中即返回、不调模型，成本最低，但纯关键词会把例外情形一起吞掉（真实案例：问「定制商品可以无理由退货吗」，FAQ 回了通用的「7 天内可退」，而语料里写着「定制类商品除外」）。现在问题里出现例外语（定制/特殊/除外/生鲜/虚拟等，可用 `FAQ_EXCEPTION_MARKERS` 配置）就不走 FAQ，改走检索拿具体条款。原则：**每条"优先命中"的捷径都必须回答"什么情况下不该走它"**。
16. **拒答必须闭环**：拒答实际有三条路——检索为空、相似度低于阈值、模型读完资料自己说"里面没有"。前两条原本就转人工，第三条以前只回一句「无法确认」就结束。现在生成后统一做一次拒答识别（`backend/app/refusal.py`，`RAG_REFUSAL_MARKERS` 可配置），命中就保留模型解释、补一句带工单号的转人工话术，`/ask` 与 `/ask/stream` 行为一致。

---

## 5. 下一步计划

优先级清单、涉及文件与验收标准写在 `PROGRESS.md` 第 5 节。概要：

1. 导入真实企业资料（PDF / 表格 / FAQ），导入后**重新校准 `RAG_MIN_SCORE`**。
2. 把仓库推到 GitHub 远程，让 CI 真实跑一次。
3. 容器故障注入测试（压测中途停后端，验证降级与恢复）。
4. 补齐：审批驳回理由、知识版本与生效时间过滤、生成质量批量报告。

已完成部分：第 1 项的"公开语料 + 重新校准"已做完（5 篇公开资料 / 74 分块、`RAG_MIN_SCORE=0.37`、导入脚本 `scripts/ingest-corpus.ps1`）；第 4 项三项都已补齐。仍未开始的是**企业自有资料接入**、**GitHub 远程 CI 实跑**和**演示视频录制**。

---

## 6. 已知问题与风险

### 环境

- **Docker Desktop 在这台机器上不稳定**：非正常退出后残留的 AF_UNIX socket 会导致启动失败，跑 `scripts/fix-docker-socket.ps1` 修复；排查记录见 `docs/FAILURE-CASES.md` 案例七。
- **Docker Hub / PyPI 直连不稳定**：Docker Hub 需 `docker.m.daocloud.io` 镜像加速；清华 PyPI 源在本网络不可达，评测与构建默认走官方源。构建用了 pip 缓存挂载，网络抖动后重跑可续传。
- 不要用 `Stop-Process` 强杀 Docker；用 `docker desktop restart` 平滑重启。

### 数据与效果

- 索引里是**公开替代语料**（5 篇 / 74 分块），不是企业自有资料；现有指标（检索 hit@1 0.96、Agent 成功率 99.33%）仍基于各自的评测语料，不能直接当作真实业务效果。
- 阈值 0.37 基于当前 5 篇公开语料（74 分块）标定，且域内/域外只剩 0.017 的间隙；换成企业自有资料必须用 `backend/evaluation/calibrate_threshold.py` 重标。成本外推值同样基于当前语料的实测 token 数。
- 索引里是**公开替代语料**（Apache-2.0 / MIT 平台说明 + 法规文本），不是企业自有资料（产品手册 / FAQ / 售后政策）；每篇语料头部都有来源与许可标注，见 `backend/corpus/README.md`。
- 知识类问题严格文案命中率 60%（FAQ 措辞与语料原文不同），该项只作参考。

### 功能缺口

- 工具层只有 5 个，`refund_request` 的"执行"是本地 mock（只建单，不动真实资金）；没有真实订单 / CRM / 支付系统接入。
- 没有多轮工具组合（一次任务只调一个业务工具）；没有知识版本与生效时间过滤。
- 生成质量（faithfulness / relevance）只有打分器，没有批量报告。

### 工程

- CI 只在本地跑过，没有远程仓库实跑。
- 没有 lint / format 脚本（前端 ESLint/Prettier、后端 ruff/black 都未接入）。
- 前端没有审批驳回理由输入框；没有演示视频。

---

## 7. 运行与验证方法

### 一键启动

双击 `start-all.bat`，或在 VS Code 里运行任务「启动全部」。启动后：

| 服务 | 地址 |
| --- | --- |
| 后端接口文档 | http://127.0.0.1:8000/docs |
| 管理员前端（5173） | http://127.0.0.1:5173/（带上传、导入、FAQ 管理、审批面板） |
| 用户前端（5174） | http://127.0.0.1:5174/（只有问答与转人工） |

### Docker

```bash
docker compose up --build -d      # 后端 8000 + 前端 5173
docker compose ps                 # rag-backend 应为 healthy
```

国内网络需要镜像加速与故障修复，见 `docs/DEPLOYMENT.md` 第 9 节。

### 测试（实测数字）

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q --basetemp=.pytest-run
# 119 passed（沙箱内跑必须给 --basetemp，否则写系统临时目录会被拒）

cd web
npm test          # 8 个文件 / 25 个用例
npm run typecheck
npm run build
```

### 评测（零 API 花费，默认不调模型）

```bash
cd backend
..\.venv\Scripts\python.exe -m evaluation.agent_eval --tag full --use-real-embedder --offline
# 150 条：任务成功率 99.33%、路由 100%、参数 100%、引用 87.32%、转人工 P 96.43% / R 100%

..\.venv\Scripts\python.exe -m evaluation.enterprise_eval --offline
# 检索：hit@1 0.96、hit@3 1.00、hit@5 1.00、MRR 0.98
```

需要真实模型时加 `--use-real-model`（会产生 API 费用；实测每次调用 230 token ≈ $0.000058）。

### 并发压测

```bash
cd backend
..\.venv\Scripts\python.exe -m evaluation.load_test --url http://127.0.0.1:8000 --concurrency 1,10,20,40,80 --requests 120
# 关限流后 600 请求零错误，吞吐约 180 RPS；默认限流 120/分钟会先触发 429（设计行为）
```

---

## 8. 不可违反的约束

### 提交与测试（来自 `AGENTS.md`）

- 每次改动后必须创建对应的 Git commit。
- 每次改动后必须编写或更新测试，交付前所有测试必须通过。

### 文件操作

- 删除重要文件前必须先说明后果并取得用户同意；日常编辑、覆盖、新建、移动可直接执行。

### 技术栈

- 前端保持 React + Vite + TypeScript + Tailwind CSS。
- 后端保持 Python + FastAPI；不引入需要独立部署的向量数据库（除非用户明确要求）。
- 检索依赖 `VectorStore` 接口，换向量库要新增实现而非改调用方。
- 现有公开函数签名保持兼容（只加不改），`workflow_mode="rag"` 行为必须与升级前一致。

### 敏感信息

- API Key、密码、token 不得写入代码、文档、日志或 Git。
- 文档里只写「Key 存在哪里」，不写值；新增环境变量要同步 `backend/.env.example`。
- 日志与轨迹写入前必须脱敏（手机号 / 邮箱 / 证件号 / Key）。

### 业务与合规

- 回答必须尽量附来源；检索不到必须拒答并建议转人工，不能编造。
- 高风险写操作必须 dry-run + 审批，幂等防重复；低风险写操作可直接执行。
- 只收录公开可下载或用户明确有权使用的资料。

---

## 9. 待用户确认的问题

- 第一批导入哪些真实资料（行业、格式、数量）。
- 是否把仓库推到 GitHub 远程并实跑 CI。
- 是否接入真实订单 / CRM / 支付系统（决定审批与幂等是否要从 mock 换成真实 adapter）。
- 延迟、成本、准确率的目标阈值分别是多少。
- 是否需要把审批从"API + 管理端面板"扩展到"驳回理由 + 审批审计报表"。
