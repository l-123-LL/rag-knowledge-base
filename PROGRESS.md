# 项目当前进度（PROGRESS）

> 最后更新：2026-09-14
> 这份文档只记录"现在做到哪、怎么验证、下一步做什么"，是每次开工的第一入口。
> 稳定内容（项目目标、架构、文件地图、决策原因、不可违反的约束）见 `HANDOFF.md`。

---

## 0. 下次会话怎么续接

新开会话时，第一句话直接说：

```text
先完整阅读 AGENTS.md、PROGRESS.md、HANDOFF.md，然后从 PROGRESS.md 第 5 节
「下一步计划」里优先级最高的一项开始做，不要依赖以前的聊天记录。
```

固定约定（来自 `AGENTS.md`）：

- 每次改动都要创建一个对应的 Git commit。
- 每次改动都要编写或更新测试，交付前所有测试和验证必须通过。
- 任何 API Key、密码、token 都不能写进代码、文档、日志或 Git。

面试材料在 `INTERVIEW.md`：里面有电梯陈述、简历条目、口述版、选型问答、踩坑故事和数字口径。**每次进度或数字变化后，要同步更新它**，否则面试时引用的数字会和项目对不上。

---

## 1. 一句话状态

企业智能客服 RAG 问答系统已打通真实闭环：资料导入 → 清洗切分 → BGE 向量 + FAISS + BM25 混合检索 → 可选 rerank → DeepSeek 生成（支持流式）→ 引用展示 → 反馈/工单/监控。

前后端可以在本机联调运行，向量索引和模型都已落盘。按功能口径完成度约 **95%**，剩下的主要是「导入真实企业资料 + 文档补齐 + 量化指标产出」这一类收尾工作，代码主干已经不需要再重写。

---

## 2. 仓库与环境事实（本次已实测确认）

| 项目 | 现状 |
| --- | --- |
| 仓库路径 | `D:\rag知识库`（本地 Git，分支 `master`，**没有配置远程仓库**） |
| 提交数 | 65 个提交，最新为 `9410abe docs: add key code comments`（2026-09-14） |
| 工作区 | 干净，`git status` 无未提交改动 |
| 前端 | React 18 + Vite 5 + TypeScript 5 + Tailwind CSS 3，开发端口 `5173` |
| 后端 | FastAPI + Uvicorn，端口 `8000` |
| Python | 项目虚拟环境 `.venv`，版本 3.12.14 |
| Node / npm | Node v24.15.0，npm 11.12.1 |
| 嵌入模型 | `BAAI/bge-large-zh-v1.5`，权重已下载到 `models/huggingface/hub/models--BAAI--bge-large-zh-v1.5` |
| 向量库 | FAISS 本地索引，落盘在 `backend/data/faiss/`（`index.faiss` + `records.json`） |
| 生成模型 | DeepSeek `deepseek-chat`，Key 在本机 `backend/.env`，未提交 |
| 管理端开关 | 前端读 `VITE_ADMIN_API_KEY`，存在时显示管理功能，不存在时就是普通用户视图 |

被 Git 忽略的运行时目录：`.venv/`、`data/`、`models/`、`backups/`、`.env`、`backend/.env`。
这些目录里是模型权重、索引、会话、日志和密钥，属于可再生成或敏感内容，**不要提交**。

---

## 3. 验证结果（本次运行的实测输出，不是估算）

### 后端测试

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

结果：**103 passed**（新增工具层、工作流、执行轨迹、Agent 评测与评测口径五组测试；覆盖切分、检索、向量库、生成、管线、意图、工具、工作流、轨迹、FAQ 存储、会话、工单、观测、备份、评估等）。

### 前端测试

```bash
cd web
npm test
```

结果：**7 个测试文件 / 22 个用例全部通过**（`npm run typecheck` 与 `npm run build` 已接入 CI）。

### 检索评估（企业客服 50 条问题集）

```bash
cd backend
..\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'.'); from evaluation.enterprise_eval import run_enterprise_evaluation; print(run_enterprise_evaluation()['average'])"
```

注意：这个入口用的嵌入是测试替身 `HashEmbedder`（64 维），**不是线上链路**，它得到的 hit@1 = 0.90、hit@3 = 0.98、hit@5 = 1.00、MRR = 0.945 只代表替身水平。用真实 `BAAI/bge-large-zh-v1.5` 复测的同一套问题是：

| 指标 | 真实 BGE（应对外引用这个） | HashEmbedder（旧口径） |
| --- | --- | --- |
| hit@1 | 0.96 | 0.90 |
| hit@3 | 1.00 | 0.98 |
| hit@5 | 1.00 | 1.00 |
| MRR | 0.98 | 0.945 |

评估集定义在 `backend/evaluation/enterprise_eval.py`：10 个客服主题 × 5 条问法 = 50 条，语料是 10 条短文本。这个规模只适合做回归基线，不能代表真实长文档效果。

### 端到端延迟与 token（真实 DeepSeek 调用，3 个问题）

| 指标 | 实测值 |
| --- | --- |
| 检索耗时（含查询向量化，CPU） | 80.6 / 81.6 / 95.6 ms |
| 首 token 延迟（SSE 流式） | 2510 / 2510 / 2967 ms |
| 流式回答总耗时 | 2642 / 2689 / 3128 ms |
| 非流式单次调用 | 5945 ms，输入 153 + 输出 34 = 187 tokens |

### 本机性能实测（CPU）

| 指标 | 实测值 | 口径 |
| --- | --- | --- |
| 单次检索延迟 | avg 73.9 ms、p50 73.4 ms、p95 79.5 ms | 10 条 chunk 索引，50 条问题 |
| 单次检索延迟 | avg 370.9 ms、p95 444.3 ms | 512 条 chunk 索引 |
| 嵌入吞吐 | 512 条 chunk 用 72.6 s（约 142 ms/chunk） | bge-large-zh-v1.5，CPU |
| 模型冷加载 | 11.1 s | 已缓存权重 |
| FAISS + BM25 建索引 | 0.83 s | 512 条，向量已算好 |
| BM25 热点 | 循环打分 88.3 ms vs 一次性打分 0.38 ms | 512 条文档，相差约 233 倍 |

### 转人工链路实测（真实管线 + 本地索引，2026-09-15）

| 问句 | 路由 | 结果 |
| --- | --- | --- |
| 我要转人工客服 | intent | 已为您转接人工客服，请稍候。（工单号 T202609154688C0） |
| 今天天气如何 | rag | 资料不足 → 已转交人工客服跟进（工单号 T2026091548F4E3） |
| 怎么联系人工客服？ | faq | 返回「服务时间工作日 9:00-18:00」（此前被意图规则拦死，现在能命中） |
| 退货要几天 | faq | 正常返回退货政策 |

阈值校准数据（同一套 10 条示例语料，真实 BGE）：50 条相关问题最高余弦相似度最小值为 0.374；8 条无关问题（天气、股票、做饭、编程等）最大值为 0.401。实测取舍：**0.42 能挡下 8/8 无关问题，但会误伤 1 条相关问题（保留 49/50）**；0.38 保留 50/50 却只能挡 7/8。当前取 0.42，属于"宁可多转人工"的取舍。

### 并发压测（2026-09-19 实测，零 API 花费）

脚本 `backend/evaluation/load_test.py`，默认只打订单 / FAQ / 转人工这些不依赖外部模型的路径。

| 场景 | 结果 |
| --- | --- |
| 默认限流（120 次/分钟/IP） | 并发 1/5/10 全部 200，P95 52–81 ms；并发 20 时全部 429（限流按设计生效） |
| 关闭限流 | 并发 1/10/20/40/80 共 600 次请求**零错误**，P95 52.6 → 81.9 → 125.6 → 210.4 → 350.8 ms |
| 吞吐上限 | 并发 20 左右饱和，约 180 RPS；并发 80 时降到 164 RPS（排队） |

口径说明：这是不调用外部模型的路径。知识问答要等 DeepSeek（首 token 2.5–3 s），CPU 版 BGE 检索吞吐此前实测约 13–16 QPS，这两个才是整链路的真实瓶颈。

### Docker 部署（2026-09-17 实机验证）

`docker compose up --build` 通过：`rag-backend` healthy、`rag-web` up、`/health` 正常、容器内订单工具能取到 mock 数据（验证 `COPY mock` 修复）、`/traces/{id}` 可回读、容器以 `uid=1000(app)` 非 root 运行；镜像 `rag-backend` 2.27 GB（CPU 版 torch）、`rag-web` 73.9 MB。详见 `docs/DEPLOYMENT.md`。

### Agent 任务评测（110 条，阶段 3 已完成）

一条命令：`cd backend && ..\.venv\Scripts\python.exe -m evaluation.agent_eval --tag full --use-real-embedder --offline`（15 秒跑完，默认不调用外部模型，**零 API 花费**；评测集构成 = 60 条新增 Agent 任务（含 10 条多轮）+ 50 条知识问答）。

| 指标 | 数值 |
| --- | --- |
| 任务成功率 | 99.09% |
| 路由 / 工具选择准确率 | 100.00% |
| 工具参数准确率 | 100.00% |
| 引用准确率 | 91.94% |
| 违规 / 幻觉率 | 0.00% |
| 转人工 Precision / Recall | 94.44% / 100.00% |
| 自动解决率 | 98.92% |
| 平均工具调用 / 平均重试 | 0.54 / 0.05 |
| P50 / P95 延迟 | 1 ms / 96 ms |

已知失败：`k38 积分有什么用？`（1/100）在阈值 0.42 下被判资料不足并转人工，属于阈值取舍的代价。报告留档在 `backend/evaluation/reports/`。

### 本机运行时数据规模

| 数据 | 位置 | 当前量级 |
| --- | --- | --- |
| 问答日志 | `backend/data/logs/ask.jsonl` | 250 条 |
| 反馈日志 | `backend/data/logs/feedback.jsonl` | 32 条 |
| FAQ | `backend/data/faqs/default.json` | 14 条 |
| 工单 | `backend/data/tickets/` | 112 个 JSON，多数由测试产生 |
| 会话记忆 | `backend/data/sessions/` | 若干 JSON |
| 向量索引 | `backend/data/faiss/records.json` | 仍是示例级小规模，**未导入真实企业资料** |

---

## 4. 已完成能力清单

### 检索与生成

- 文本切分：按段落聚合 + 窗口切分，可配置块大小和重叠。
- 父子切分（`HIERARCHICAL_CHUNKING=true` 开启）：子块用于检索、父块用于生成，避免长文档答案被切分边界截断；父块文本存在子块 metadata 里，代价是索引体积变大。
- 嵌入：`BAAI/bge-large-zh-v1.5`，`normalize_embeddings=True`，内积检索。
- 向量库：`VectorStore` 接口 + `FAISSVectorStore` 实现，元数据与索引分离落盘，重启可恢复。
- 关键词检索：`rank-bm25` + `jieba` 中文分词。
- 混合检索：向量与 BM25 融合，`top_k` 可传参（默认 5）。
- 可选 rerank：配置 `RERANK_MODEL` 后启用 BGE reranker。
- 生成：DeepSeek 客户端，支持普通与 SSE 流式两种调用。
- 兜底：检索不到可靠内容时返回「资料不足」而不是编造。

### 企业客服业务逻辑

- FAQ 优先命中：命中标准问题直接返回标准答案，不调用大模型。
- 意图路由：用规则识别投诉和明确的转人工请求，命中后跳过检索与生成；带防误判（「我不想转人工」不会触发）。
- 转人工统一出口 `escalate_to_human`：明确要求转人工、投诉、以及**检索不到或相似度低于阈值**这四种情况都会建工单并返回带工单号的引导话术，`/ask` 与 `/ask/stream` 行为一致。
- 低相关性兜底：`RAG_MIN_SCORE` 用原始余弦相似度做阈值（归一化分数永远有最大值 1.0，不能用它做绝对判断）；示例语料校准值为 0.42，默认 0 表示关闭。
- 工单支持 `GET /tickets` 查询与可选 Webhook 外发到 CRM。
- 会话记忆：前端自动带 `session_id`，后端持久化最近对话。
- 多租户隔离：`X-Tenant-ID` 隔离来源、FAQ、会话、工单和检索元数据。
- 资料可停用/恢复，停用后自动排除出检索结果。

### 可选工具工作流（最小改动升级 · 阶段 1 已完成）

- `workflow_mode="tools"` 可选分支：默认 `rag` 保持升级前行为不变，`/ask` 与 `/ask/stream` 都已支持。
- 4 个工具：`knowledge_search`、`order_lookup`、`logistics_track`、`human_handoff`，每个都有 Pydantic 输入输出、统一错误码、超时（默认 3 s）与重试（默认 1 次）。
- 最小状态机：规则意图 → 订单/物流工具 → FAQ → 知识检索 → 转人工；最多 3 次业务工具调用，转人工不占步骤预算；总超时默认 15 s，超时或连续失败一律降级。
- 订单查不到时不再回退到宽泛 FAQ（避免误导），改为知识检索，仍无结果才转人工。
- 执行轨迹：`trace_id` + 按天 JSONL + `GET /traces/{trace_id}`，写入前对手机号、邮箱、证件号、疑似 Key 脱敏。
- 前端（阶段 2 已完成）：顶部「RAG 问答 / 工具工作流」切换、Trace 面板（步骤、工具、重试、token、成本、转人工原因），工具模式走非流式接口以拿到 `trace_id`。
- 输入护栏（阶段 3 新增）：命中提示词注入、密钥探测、跨租户尝试等模式时直接转人工，不进入检索与生成，原因记为 `unsafe_request`。
- 评测分档：`--tag smoke|core|full`（25 / 60 / 110 条）与 `--limit`，日常只跑冒烟，里程碑跑全量并留档。
- 多轮指代（新增）：追问里没带订单号时，从最近几轮用户消息里取上一个订单号（「它的物流到哪了」），并在轨迹里记录 `resolve` 步骤与 `reused_from_history` 标记。
- mock 数据位于 `backend/mock/orders.json`（20 条订单 + 10 条物流，含 acme 租户样本用于隔离验证），刻意不放被 gitignore 的 `data/`。

### 知识库管理

- 导入 TXT / Markdown / HTML / 文本层 PDF；PDF 表格可提取为 Markdown。
- 网页 URL 抓取导入并清洗正文。
- FAQ 增删改查 + 版本号，本地持久化。
- 扫描版 PDF 的 OCR 作为可选钩子（`OCR_ENABLED=true` 需装 OCR 组件）。

### 可观测与运维

- `/stats` 资料数、分片数、会话数、FAQ 数、工单数。
- `/metrics` 查询量、平均延迟、总 token、成本、有帮助率。
- `/alerts` 按延迟和低有帮助率输出告警。
- 结构化 JSONL 日志 + 可选观测 Webhook（可接 Langfuse 类平台）。
- 管理员 API Key + 每分钟限流（默认关闭）。
- 可选 OIDC/SSO 校验钩子（`OIDC_JWKS_URL`）。
- 管理员备份接口 `POST /backup`。

### 工程化

- 前端企业客服工作台界面，管理功能仅管理员可见。
- 前端错误边界、mock 回退、流式失败自动降级。
- 后端 / 前端 Dockerfile + `docker-compose.yml`。
- GitHub Actions CI：推送或 PR 时跑后端测试、前端测试、类型检查、构建。

---

## 5. 下一步计划（按优先级，从上往下做）

### P0-0 修掉评估口径和 BM25 性能热点（本次新发现，建议先做）

要做什么：

1. `backend/app/evaluation.py` 的 `run_retrieval_evaluation` 默认注入 `HashEmbedder`，导致 `python -m evaluation.enterprise_eval` 输出的是测试替身成绩（hit@1 = 0.90），和线上链路（BGE，hit@1 = 0.96）不是一个口径。改成可传入 embedder，命令行默认用真实模型，测试里显式传替身。
2. `backend/app/retrieval.py` 的 `BM25Index.score(query, index)` 内部每次重算全量分数，`HybridRetriever.search` 逐文档调用它，复杂度 O(N²)。实测 512 条文档下循环调用 88.3 ms、一次性打分 0.38 ms（233 倍差距），索引越大检索越慢。

涉及：`backend/app/evaluation.py`、`backend/app/retrieval.py`、`backend/evaluation/enterprise_eval.py`、`backend/tests/test_evaluation.py`、`backend/tests/test_retrieval.py`。
验收：评估入口默认走真实模型；512 条索引下检索 p95 明显下降；原有测试全绿并补新测试。

### P0-1 导入真实企业资料，跑通真实问答

要做什么：准备若干份真实客服资料（FAQ 表格、产品手册、售后政策 PDF/Markdown），通过 `/ingest`、`/ingest/file` 或前端「上传资料」导入，然后用 10~20 个真实问题验证回答质量。
涉及：`backend/app/ingestion.py`、`backend/app/main.py`、`backend/data/`（运行时产生）。
产出：真实索引规模 + 一组真实问答记录；**导入后要重新采样校准 `RAG_MIN_SCORE`**（当前 0.42 只适用于 10 条示例语料）。

### P0-2 补齐项目说明文档

要做什么：新增 `README.md`（是什么、怎么启动、界面截图位、接口列表），新增 `docs/ROADMAP.md`（已完成/进行中/未开始）和 `docs/RAG_DESIGN.md`（数据、切分、Embedding、向量库、检索、Prompt、评估的选型与理由）。
涉及：新增 `README.md`、`docs/ROADMAP.md`、`docs/RAG_DESIGN.md`。

### P1-1 清理医学阶段遗留内容

要做什么：`backend/evaluation/sample_corpus.json`、`backend/evaluation/sample_questions.json` 仍是医学问题，`backend/app/__init__.py` 的 docstring 还写着「医学知识库」。统一改成企业客服样例，或明确标注为历史样例。
涉及：`backend/evaluation/`、`backend/app/__init__.py`、`backend/tests/test_evaluation.py`。

### P1-2 产出延迟与成本量化数字

已实测的部分：首 token 2.51 / 2.51 / 2.97 s，流式总耗时 2.64 / 2.69 / 3.13 s，单次查询 187 tokens（输入 153 + 输出 34）。剩下来要做的：在 `backend/.env` 填入 DeepSeek 单价（`DEEPSEEK_INPUT_PRICE_PER_MILLION`、`DEEPSEEK_OUTPUT_PRICE_PER_MILLION`），把 token 折算成金额并写进 `README.md`；样本量也要从 3 个问题扩到几十个。
涉及：`backend/.env`（本地，不提交）、`backend/app/cost.py`、`backend/data/logs/ask.jsonl`。

### P1-3 验证 rerank 的实际收益

要做什么：设置 `RERANK_MODEL=BAAI/bge-reranker-v2-m3`，用同一套 50 条问题做开关对比，记录 hit@1 / MRR 变化，并记录额外延迟。
涉及：`backend/app/reranker.py`、`backend/evaluation/enterprise_eval.py`。

### P2-1 代码规范与部署验证

要做什么：加 ESLint + Prettier（前端）与 ruff/black（后端）；实际执行一次 `docker compose up` 验证两个镜像能构建并连通。
涉及：`web/package.json`、`backend/requirements.txt`、`docker-compose.yml`、`.github/workflows/ci.yml`。

### P2-2 扩充评估集

要做什么：把 50 条扩到 200 条左右，补上生成质量（faithfulness / relevance）报告，做成可重复运行的脚本。
涉及：`backend/evaluation/enterprise_eval.py`、`backend/evaluation/generation_eval.py`、`backend/app/judge.py`。

---

## 6. 已知问题与风险

- **索引里还是示例文本**：`backend/data/faiss/records.json` 规模很小，真实资料尚未导入，因此现有指标只代表示例语料，不能当作真实业务效果。
- ~~评估入口口径不一致~~ → 已修复：命令行默认注入真实模型（`--embedder bge`，可切 `hash` 做快速回归），测试替身只保留给单元测试；同时加 `--offline` 跳过联网校验（150 秒 → 17 秒）。
- **BM25 的 O(N²) 已修复**：新增 `BM25Index.scores()` 一次性打分，检索层改为单次调用（保留原 `score()` 签名）。512 条索引实测检索从平均 370.9 ms / P95 444.3 ms 降到 **187.5 ms / 193.4 ms**，结果与逐文档打分完全一致（有单测）。
- **成本数字缺失**：`DEEPSEEK_*_PRICE_PER_MILLION` 目前为 0，`/metrics` 的成本字段没有实际意义。
- **rerank 未实测**：代码路径存在，但从未开启对比过效果。
- **OCR 未实测**：只有钩子，扫描版 PDF 实际效果未知。
- **Docker 未实测构建**：文件齐全，但没有在本机跑过 `docker compose up`。
- **评估集偏小且偏理想**：50 条问题都来自 10 条短文本，hit@1 = 0.96 不能代表真实长文档场景。
- **相关性阈值需要重新校准**：`RAG_MIN_SCORE=0.42` 是在 10 条示例语料上校准的（相关组最低 0.374、无关组最高 0.401，间隔只有 0.027）。换成真实企业资料后必须重新采样校准，否则会误拒答或漏拒答。
- **转人工只是“登记 + 话术”**：没有坐席排队、分配、实时会话，也没有转人工后的消息回流；工单目前只落盘成 JSON，可选 Webhook 外发。
- **没有 lint / format 脚本**，靠人工约定风格。
- **没有 README 和设计文档**，新人只能靠 `HANDOFF.md` + `PROGRESS.md`。
- **移动端只做过手动检查**，没有自动化浏览器回归。
- **鉴权是可选钩子**：默认单机演示无鉴权，上生产前必须配置 `ADMIN_API_KEY` 和 OIDC。
- **本机密钥**：`backend/.env` 里有真实 DeepSeek Key；换机器时需要重新配置，且绝不能提交。
- **没有远程仓库**：目前只在本地，代码没有异地备份。
- ~~管理员 Key 可能被打进前端镜像~~ → 已修复：`web/.dockerignore` 排除 `.env`（保留不含密钥的 `.env.user`）。
- **鉴权默认关闭**：未配置 `ADMIN_API_KEY` / `OIDC_JWKS_URL` 时启动会打印警告，公网部署前必须补齐。

---

## 7. 常用命令速查

### 一键启动（推荐给演示和非开发场景）

双击项目根目录的 `start-all.bat`，会自动开三个窗口并启动：

| 服务 | 地址 |
| --- | --- |
| 后端接口文档 | `http://127.0.0.1:8000/docs` |
| 管理员版前端 | `http://127.0.0.1:5173/` |
| 用户版前端 | `http://127.0.0.1:5174/` |

关掉那三个窗口即停止服务。也可以单独双击 `start-backend.bat` / `start-admin-web.bat` / `start-user-web.bat`。

在 VS Code 里等价的操作：`终端 → 运行任务`，选「启动全部（后端 + 管理端 + 用户端）」，任务定义在 `.vscode/tasks.json`。

两个前端的区别来自环境变量：管理员版读 `web/.env` 里的 `VITE_ADMIN_API_KEY`；用户版用 `--mode user`，由 `web/.env.user` 把该变量置空（`web/.env.user` 不含密钥，可以提交）。两个脚本都加了 `--strictPort`，端口被占用会直接报错，不会偷偷换端口。

```bash
# 启动后端（端口 8000）
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 启动前端（端口 5173，已配置 /api 代理到 8000）
cd web
npm run dev

# 后端测试
cd backend
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q

# 前端测试 / 类型检查 / 构建
cd web
npm test
npm run typecheck
npm run build

# 检索评估
cd backend
..\.venv\Scripts\python.exe -m evaluation.enterprise_eval
```

前端普通用户视图：直接访问 `http://127.0.0.1:5173/`（`web/.env` 里没有 `VITE_ADMIN_API_KEY` 时看不到管理功能）。
管理视图：在 `web/.env` 里设置 `VITE_ADMIN_API_KEY`（值与后端 `ADMIN_API_KEY` 一致）后重启前端。

---

## 8. 待用户确认的事

- 第一批要导入哪些真实资料（行业、格式、大概多少份）。
- 是否需要把仓库推到 GitHub 作为远程备份。
- 单次查询成本和延迟的目标阈值是多少。
- 是否要正式做 OCR 和复杂表格解析。
- 是否会真的上线（决定要不要把鉴权、限额、备份做成必选而不是可选）。
