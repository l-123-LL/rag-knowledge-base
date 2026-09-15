# 项目交接文档

> 目标：让新的 AI 只读 `AGENTS.md` + `HANDOFF.md` + `PROGRESS.md` 就能无缝接手，不依赖任何聊天记录。
> 分工：本文件写**稳定内容**（目标、架构、文件地图、决策原因、约束、运行方式）；**会变的内容**（做到哪、验证数字、下一步）写在 `PROGRESS.md`，开工前先读它。
> 未实现的内容一律标注「计划」，避免把设计当成已完成。

---

## 1. 项目目标

### 做什么

构建一个面向企业的智能客服问答系统：

- 从产品手册、FAQ、售后政策、物流规则等企业资料中检索内容。
- FAQ 精确命中优先，未命中再走 RAG 检索 + DeepSeek 生成。
- 低置信度、投诉、需要人工介入的问题转人工客服，并自动建工单。
- 回答必须附来源引用，检索不到时明确说「资料不足」，不编造。
- 不能泄露内部价格、客户隐私等敏感信息。

### 给谁用

- 企业客户：在网页上自助提问。
- 客服与运营人员：维护资料、FAQ 和工单（管理视图）。
- 当前阶段的实际使用者：项目作者本人，用于验证客服问答流程和拿量化指标。

### 成功标准

- 能导入企业资料（TXT / Markdown / HTML / 文本层 PDF / 网页 URL）并建立索引。
- 标准 FAQ 直接答疑，非标准问题由资料生成答案并附引用。
- 无法可靠回答时建议转人工，而不是给一个像样的错误答案。
- 有可重复运行的评估，能给出检索命中率、生成质量、延迟和成本量化数字。
- 每次改动都有 Git commit，且测试全部通过后才交付。

### 项目方向的一次变更（重要）

项目最初是「医学知识库 RAG」。中途按用户要求整体转向**企业智能客服**。当前代码、提示词、示例数据、界面和评估集都已是客服方向；医学阶段的残留内容见第 6 节。

---

## 2. 当前进度

**详细进度、实测数字和下一步计划请看 `PROGRESS.md`**，本文件不再重复维护那份清单，避免两份文档互相打架。

这里只留一句结论：真实 RAG 闭环已经打通（导入 → 切分 → BGE + FAISS + BM25 混合检索 → 可选 rerank → DeepSeek 流式生成 → 引用展示 → 反馈 / 工单 / 监控），前后端可本机联调运行，剩余工作集中在导入真实企业资料、补齐文档和产出量化指标。

---

## 3. 文件地图

所有路径都是相对项目根目录的相对路径。

### 根目录

- `AGENTS.md`：强制规则，新 AI 必须先读。
- `PROGRESS.md`：当前进度、实测数字、下一步计划（每次开工先读）。
- `HANDOFF.md`：本文件，稳定背景与约定。
- `INTERVIEW.md`：面试材料（电梯陈述、简历条目、选型问答、踩坑故事、数字口径），数字变化时要同步更新。
- `start-all.bat`：一键启动后端 + 管理员前端 + 用户前端（双击即可）。
- `start-backend.bat`、`start-admin-web.bat`、`start-user-web.bat`：单独启动某个服务。
- `.vscode/tasks.json`：VS Code 任务，等价于上面几个启动脚本。
- `docker-compose.yml`：后端 + 前端两个服务的编排。
- `.gitignore`：忽略 `.venv/`、`data/`、`models/`、`backups/`、`.env`、`backend/.env`。
- `.github/workflows/ci.yml`：CI，推送或 PR 时跑后端测试、前端测试、类型检查、构建。

### 后端入口与基础

- `backend/app/main.py`：FastAPI 应用入口，所有接口定义在这里。
- `backend/app/schemas.py`：请求 / 响应 Pydantic 模型。
- `backend/app/config.py`：加载 `backend/.env` 环境变量。
- `backend/app/factory.py`：RAG 管线的依赖注入工厂，把嵌入、向量库、检索、生成组装起来。
- `backend/app/mock_data.py`：示例来源数据（首次启动展示用）。
- `backend/.env.example`：环境变量清单示例，**不含真实密钥**。
- `backend/requirements.txt`：Python 依赖。
- `backend/Dockerfile` / `backend/.dockerignore`：后端容器镜像。

### 后端 RAG 核心

- `backend/app/chunking.py`：文本归一化、按段落聚合和窗口切分，块大小与重叠可配置。
- `backend/app/embeddings.py`：`Embedder` 接口、测试用 `HashEmbedder`、生产用 `SentenceTransformerEmbedder`（`BAAI/bge-large-zh-v1.5`）。
- `backend/app/vector_store.py`：`VectorStore` 接口、内存实现和 `FAISSVectorStore`（索引与元数据分开落盘）。
- `backend/app/retrieval.py`：jieba 分词、BM25、混合检索器和检索结果模型。
- `backend/app/reranker.py`：可选重排序器，默认 `BAAI/bge-reranker-v2-m3`，由 `RERANK_MODEL` 开关。
- `backend/app/generation.py`：DeepSeek 生成客户端，支持普通与流式。
- `backend/app/pipeline.py`：把检索与生成串成 `RAGPipeline`，含「资料不足」判定。
- `backend/app/ingestion.py`：TXT / Markdown / HTML / 文本层 PDF 读取清洗，PDF 表格转 Markdown，网页正文抓取。

### 后端业务与运维

- `backend/app/faq_store.py`：FAQ 本地持久化，增删改查与版本号。
- `backend/app/intent.py`：规则意图路由（投诉、转人工等）。
- `backend/app/session_store.py`：会话记忆持久化。
- `backend/app/ticket_store.py`：工单创建与查询。
- `backend/app/tenant.py`：多租户隔离，通过 `X-Tenant-ID` 区分数据。
- `backend/app/security.py`：可选管理员 Key 与 OIDC/JWT 校验。
- `backend/app/observability.py`：问答与反馈的结构化 JSONL 日志、可选监控 Webhook。
- `backend/app/cost.py`：按配置单价估算 token 成本。
- `backend/app/backup.py`：把数据目录打包成备份。
- `backend/app/judge.py`：生成质量打分（faithfulness / relevance）。

### 后端测试与评估

- `backend/tests/`：pytest 测试，覆盖切分、检索、向量库、生成、管线、意图、FAQ、会话、工单、观测、备份、评估、接口。其中 `test_intent.py` 专测意图关键词与防误判。
- `backend/evaluation/enterprise_eval.py`：50 条企业客服检索评估集与运行入口。
- `backend/evaluation/run_eval.py`：从 JSON 文件读取语料和问题跑检索评估。
- `backend/evaluation/generation_eval.py`：生成质量评估。
- `backend/evaluation/sample_corpus.json` / `sample_questions.json`：医学阶段的示例数据，**待清理**。

### 前端 `web/`

- `web/index.html`：HTML 入口。
- `web/vite.config.js`：开发服务器（端口 5173）与 `/api` 到 `127.0.0.1:8000` 的代理，以及 Vitest 配置。
- `web/.env.user`：用户视图模式的环境文件，把 `VITE_ADMIN_API_KEY` 置空，配合 `npm run dev -- --mode user --port 5174` 使用（不含密钥，可以提交）。
- `web/package.json`：依赖与脚本（`dev` / `build` / `test` / `typecheck` / `preview`）。
- `web/Dockerfile` / `web/nginx.conf`：前端镜像与静态托管 + 反向代理。

### 前端源码

- `web/src/main.tsx`：React 真正入口，挂载 `App` 和错误边界。
- `web/src/App.tsx`：页面骨架与全部状态管理，按 `VITE_ADMIN_API_KEY` 决定是否渲染管理功能。
- `web/src/types.ts`：`Source`、`Citation`、`Conversation`、`Stats`、`Metrics` 等类型。
- `web/src/api/client.ts`：API 抽象层，负责请求 `/api/ask`、`/api/sources`、上传、FAQ 等，并带租户 ID 与可选管理员 Key。
- `web/src/data/mockData.ts`：后端不可用时的示例来源与本地兜底回答。
- `web/src/components/SourcePanel.tsx`：左侧来源面板、统计、FAQ 管理入口。
- `web/src/components/ChatPanel.tsx`：右侧问答主流程、消息列表与错误提示。
- `web/src/components/QuestionInput.tsx`：输入框与发送状态。
- `web/src/components/AnswerCard.tsx`：单条问答卡片，处理加载、答案、资料不足和反馈。
- `web/src/components/CitationList.tsx`：引用折叠与逐条展开。
- `web/src/components/ErrorBoundary.tsx`：渲染异常兜底页。
- `web/src/components/icons.tsx`：内联 SVG 图标。
- `web/src/test/setup.ts`：测试环境初始化。
- `web/src/**/*.test.ts(x)`：6 个测试文件，共 19 个用例。

### 入口文件速查

- 前端 HTML：`web/index.html`
- 前端 JS：`web/src/main.tsx`
- 后端：`backend/app/main.py`

---

## 4. 关键决策及原因

### 4.1 前端技术栈：React + Vite + TypeScript + Tailwind

**决策：** React 18、Vite 5、TypeScript 5、Tailwind CSS 3。
**原因：** Vite 冷启动快、适合本地反复调试；TypeScript 让前后端接口对接出错更早暴露；Tailwind 便于维持一套统一的浅色专业界面。项目已经稳定运行在这套栈上，除非用户明确要求，不要换框架。

### 4.2 视觉风格：企业工作台，而不是营销页

**决策：** 白底、蓝色主色、低饱和边框、信息密度偏高的工作台布局，管理功能按角色隐藏。
**原因：** 使用场景是客服坐席和运营人员长时间使用，需要可扫描、可重复操作，不需要首页 hero 和大面积装饰。

### 4.3 后端：FastAPI + 本地模型 + DeepSeek

**决策：** Python FastAPI；嵌入用本地 `BAAI/bge-large-zh-v1.5`；生成用云端 DeepSeek `deepseek-chat`。
**原因：**

- 嵌入放在本地，中文效果好、不产生每千次调用的嵌入费用，资料也不用出内网。
- 生成放云端，是因为本地跑生成模型对这台机器的显存和部署复杂度都不划算。
- FastAPI 自带 OpenAPI 文档，接口调试成本低，且与 pytest / httpx 配合成熟。

### 4.4 向量库选 FAISS，而不是 Chroma / pgvector / Milvus

**决策：** `FAISSVectorStore`，`IndexFlatIP` + 归一化向量，元数据单独存 JSON。
**原因：**

- 当前是单机、小规模（几百到几万条 chunk）场景，FAISS 无需额外服务进程，装一个包就能用。
- Chroma 抽象更重、版本变动频繁；pgvector 需要先引入 Postgres；Milvus 需要独立部署，对现阶段都是纯负担。
- 代码里已抽出 `VectorStore` 接口，将来换 pgvector 或 Milvus 只需要新增一个实现，不动检索和管线代码。

### 4.5 检索用「向量 + BM25」混合，而不是纯向量

**决策：** 向量检索与 `rank-bm25` 融合，中文分词用 jieba，结果融合后取 `top_k`（默认 5）。
**原因：** 客服问题里大量是订单号、型号、专有名词、政策条款名，纯向量检索对这些精确词面匹配不稳定；BM25 能补上这一块。这也是 50 条评估集能做到 hit@1 = 0.90 的主要原因。

### 4.6 rerank 做成可选开关

**决策：** `RERANK_MODEL` 为空时跳过 rerank，配置后启用 BGE reranker。
**原因：** 本地首次加载 rerank 模型要下载几百 MB 权重并明显增加单次延迟；默认关闭保证项目开箱能跑，需要精度时再打开。

### 4.7 FAQ 优先，RAG 兜底，规则先于模型

**决策：** 命中标准 FAQ 直接返回标准答案，不调用大模型；投诉 / 转人工由规则意图路由处理。
**原因：** 客服场景里最高频的问题往往是标准问题，走 FAQ 可以做到零延迟、零成本、答案百分之百一致；规则路由比让模型判断更稳定可控。

### 4.8 检索不到就拒答

**决策：** 检索为空、或最高原始余弦相似度低于 `RAG_MIN_SCORE` 时判定「资料不足」，不调用模型，并且**建工单 + 返回带工单号的转人工话术**，而不是只回一句「不知道」。
**原因：** 客服场景编造答案的代价（错误政策、错误承诺）远高于说一句「我帮您转人工」；但只拒答不给出口会让用户卡死，所以拒答必须和转人工绑在一起。

### 4.11 转人工只走规则 + 阈值兜底，不让模型决定

**决策：** 三条入口——(1) 规则意图命中「转人工 / 转接人工 / 人工服务 / 人工坐席 / 找人工 / 客服电话」或「投诉」；(2) 检索为空；(3) 相似度低于 `RAG_MIN_SCORE`。三条都走同一个 `escalate_to_human`，建工单并把工单号拼进话术。

**原因：**

- 让模型判断「该不该转人工」会引入不稳定；规则命中就短路，检索和生成都不执行，成本和延迟同时降下来。
- 关键词必须做否定词过滤（「我不想转人工」不能触发），也要刻意不收「人工客服」这类描述性说法，否则「怎么联系人工客服？」会被拦死、永远命中不了 FAQ 里的服务时间。
- 阈值只能用原始余弦相似度：`HybridRetriever` 返回的 `combined/dense` 分数是 min-max 归一化结果，永远有最大值 1.0，做不了绝对判断，所以 `RetrievedChunk` 额外带了 `raw_dense_score`。
- 阈值做成环境变量（默认 0 关闭），因为它是随语料变化的校准值，写死在代码里会在换库时误拒答。

### 4.9 Key 只放本地 `.env`

**决策：** `backend/.env` 存 DeepSeek Key 和各类开关，`.gitignore` 已忽略；仓库只提交 `backend/.env.example`。
**原因：** 防止密钥泄露。文档里只写变量名，绝不写值。

### 4.10 多租户、鉴权、OCR、Webhook 做成「可选钩子」

**决策：** 这些生产级能力都实现为配置后才生效，默认关闭。
**原因：** 现阶段是单机演示，默认全开会让本地启动变重；但提前留好接口和数据结构，上生产时改配置即可，不用重构。

---

## 5. 下一步计划

优先级清单、每项涉及的文件和完成标准，统一维护在 `PROGRESS.md` 第 5 节。这里是概览：

1. **P0** 导入真实企业资料，跑通真实问答并记录数字。
2. **P0** 补 `README.md`、`docs/ROADMAP.md`、`docs/RAG_DESIGN.md`。
3. **P1** 清理医学阶段残留（`backend/evaluation/sample_*.json`、`backend/app/__init__.py` docstring）。
4. **P1** 配置 DeepSeek 单价，产出延迟与成本量化表。
5. **P1** 开启 rerank 做开关对比，量化收益。
6. **P2** 加 lint / format，实测 Docker 构建，扩充评估集并补生成质量报告。

---

## 6. 已知问题与风险

### 数据与效果

- 向量索引里目前只有示例级文本，真实企业资料尚未导入，现有指标不能代表真实业务效果。
- 50 条评估集规模偏小、文本偏短且理想化，hit@1 = 0.96（真实模型口径）属于乐观数字。
- 评估入口 `run_retrieval_evaluation` 默认注入测试替身 `HashEmbedder`，命令行输出的是替身成绩（hit@1 = 0.90）；真实 `bge-large-zh-v1.5` 复测为 hit@1 = 0.96、MRR = 0.98。对外引用必须用真实模型口径，代码待修。
- 转人工阈值 `RAG_MIN_SCORE=0.42` 是在 10 条示例语料上校准的（相关 50 条最低 0.374、无关 8 条最高 0.401，间隔仅 0.027），换真实语料后必须重新采样校准。
- 转人工只做到「建工单 + 返回话术」：没有坐席排队、坐席分配、实时会话，也没有转人工后的消息回流。
- 扫描版 PDF 和复杂表格只留了 OCR 钩子，未实测。
- rerank 代码路径存在，但从未做开关对比。

### 量化缺失

- `DEEPSEEK_INPUT_PRICE_PER_MILLION` / `DEEPSEEK_OUTPUT_PRICE_PER_MILLION` 目前为 0，`/metrics` 里的成本没有实际意义。
- 没有系统的首 token 延迟和并发压测数据，`ask.jsonl` 里有原始 `latency_ms` 但未汇总成报告。

### 工程质量

- 没有 lint / format 脚本（ESLint、Prettier、ruff、black 都未接入）。
- `BM25Index.score` 每次调用都重算全量分数，`HybridRetriever.search` 逐文档调用，复杂度 O(N²)：512 条文档时循环打分 88.3 ms，一次性打分只要 0.38 ms，索引变大后检索会明显变慢。
- 没有 `README.md`、`docs/ROADMAP.md`、`docs/RAG_DESIGN.md`。
- Docker 文件齐全，但未在本机实测构建与启动。
- 前端移动端只做手动检查，没有自动化浏览器回归。
- 仓库只有本地 Git，没有远程备份。

### 安全与合规

- 默认单机演示无鉴权；上生产前必须配置 `ADMIN_API_KEY` 和 OIDC。
- `backend/.env` 存有真实 DeepSeek Key，换机器需重新配置，绝不能提交。
- 只收录官方公开资料和用户明确有权使用的资料，不抓取受版权保护的付费内容。
- 回答必须附来源，资料不足必须拒答，不能编造政策、价格或承诺。

### 遗留内容

- `backend/evaluation/sample_corpus.json`、`backend/evaluation/sample_questions.json` 仍是医学问题。
- `backend/app/__init__.py` 的 docstring 仍写着「医学知识库后端应用包」。

### 未验证部分

- 真实 PDF 语料（尤其是表格和排版复杂的手册）的解析效果。
- Docker 镜像构建与 `docker compose up` 的实际连通性。
- 多租户隔离、OIDC 校验、OCR、Webhook 外发在真实环境下的表现。
- 前端在窄屏和移动端的自动化回归。

---

## 7. 运行与验证方法

### 一键启动（推荐）

双击项目根目录的 `start-all.bat`，或在 VS Code 里运行任务「启动全部（后端 + 管理端 + 用户端）」。启动后：

- 后端接口文档 `http://127.0.0.1:8000/docs`
- 管理员版前端 `http://127.0.0.1:5173/`（带上传、导入、FAQ 管理等入口）
- 用户版前端 `http://127.0.0.1:5174/`（只有问答和转人工按钮）

窗口关闭即停止服务。手动启动的等价命令见本节下方。

### 环境信息（本机实测）

- Node.js `v24.15.0`，npm `11.12.1`
- Git `2.55.0.windows.5`
- Python 使用项目虚拟环境 `.venv`，版本 3.12.14

### 启动后端（端口 8000）

```bash
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 启动前端（端口 5173，已代理 `/api` 到后端）

```bash
cd web
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:5173/`。

### 测试与构建

```bash
# 后端：当前 65 passed
cd backend
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q

# 前端：当前 6 个文件 / 19 个用例通过
cd web
npm test
npm run typecheck
npm run build
```

### 检索评估

```bash
cd backend
..\.venv\Scripts\python.exe -m evaluation.enterprise_eval
```

当前结果：hit@1 = 0.90、hit@3 = 0.98、hit@5 = 1.00、MRR = 0.945。

### Docker 启动（尚未实测）

```bash
docker compose up --build
```

### Git 状态

```bash
git status --short --branch
git log --oneline --decorate --all
```

---

## 8. 不可违反的约束

### 提交与测试（来自 `AGENTS.md`）

- 每次改动后必须创建对应的 Git commit。
- 每次改动后必须编写或更新相关测试，交付前所有测试和验证必须通过。

### 文件操作

- 删除重要文件（个人资料、项目代码、配置等难以恢复的内容）前必须先说明后果并取得用户同意。
- 日常的编辑、覆盖、新建、移动可以直接执行。

### 技术栈

- 前端保持 React + Vite + TypeScript + Tailwind CSS，不要擅自换框架或改成静态页。
- 后端保持 Python + FastAPI，不要引入需要独立部署的向量数据库，除非用户明确要求。
- 检索代码依赖 `VectorStore` 接口，换向量库要新增实现而不是改调用方。

### 敏感信息

- 任何 API Key、密码、token 都不能写进代码、文档、日志或 Git。
- 文档里只写「Key 存在哪里」，不写值。
- 新增环境变量要同步更新 `backend/.env.example`。

### 业务与合规

- 回答必须尽可能附来源引用。
- 检索不到时必须明确拒答并建议转人工，不能编造。
- 不抓取受版权保护或需付费的资料。
- 涉及价格、承诺、隐私的问题必须保守处理。

---

## 9. 待用户确认的问题

- 第一批要导入哪些真实资料：行业、来源、格式、大概多少份。
- 是否需要配置远程 GitHub 仓库做备份。
- 延迟、成本、检索命中率、答案准确率的目标阈值分别是多少。
- 是否要正式做扫描版 OCR 和复杂表格解析。
- 是否会真实上线：如果是，鉴权、限流、备份需要从可选变成必选。
- 是否需要多租户和 SSO 落地，还是保持当前可选钩子即可。
