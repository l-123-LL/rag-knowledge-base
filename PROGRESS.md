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

企业智能客服 RAG 问答系统已打通真实闭环：资料导入 → 清洗切分 → BGE 向量 + FAISS + BM25 混合检索 → 可选 rerank → DeepSeek 生成（支持流式）→ 引用展示 → 反馈/工单/监控。索引里已经是 **5 篇许可清晰的公开语料 / 74 个分块**，拒答阈值按实测重新标定为 **0.37**。

前后端可以在本机联调运行，向量索引和模型都已落盘，Docker 也能一键起。按功能口径完成度约 **96%**，剩下的主要是「导入企业自有资料并重标阈值 + GitHub 远程 CI 实跑 + 演示视频」这一类收尾工作，代码主干已经不需要再重写。

---

## 2. 仓库与环境事实（本次已实测确认）

| 项目 | 现状 |
| --- | --- |
| 仓库路径 | `D:\rag知识库`（本地 Git，分支 `master`，**没有配置远程仓库**） |
| 提交数 | 114 个提交（2026-09-19：检索分块 id 撞车修复 + 5 篇公开语料入库 + 阈值重标 + 来源面板接真实索引 + nginx 动态解析） |
| 当前语料 | `backend/corpus/` 5 篇公开资料（Apache-2.0 / MIT / 法律法规文本），导入后 **74 个分块**；导入脚本 `scripts/ingest-corpus.ps1` |
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

结果：**138 passed**（2026-09-19 本轮新增 10 条：重复 id 下分数不错位、分块 id 跨资料唯一、重复导入跳过重复 id、重复导入幂等、FAISS 分数与点积一致、records.json 顺序按内部 id、阈值标定三个纯逻辑用例、来源列表跟随真实索引；覆盖切分、检索、向量库、生成、管线、意图、工具、工作流、轨迹、审批、FAQ、会话、工单、观测、备份、评估等）。

### 前端测试

```bash
cd web
npm test
```

结果：**8 个测试文件 / 26 个用例全部通过**（`npm run typecheck` 与 `npm run build` 已接入 CI）。

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

### 检索评估（真实语料 20 条标注问题，2026-09-19）

上面那套是短文本、一问一答几乎一一对应，hit@1 = 0.96 说明不了长文档上的表现。所以在 `backend/corpus/` 的真实资料上另做了一套：

```bash
cd backend
..\.venv\Scripts\python.exe -m evaluation.corpus_eval
```

5 篇资料 / 74 个分块；20 条问题，每条标注「期望命中的文档 + 证据关键词」；区分两种口径——`doc_hit@k` 只看文档对不对，`evidence_hit@k` 还要求命中那段里真的出现证据句（更接近「能不能答对」）。

| 指标 | 数值 |
| --- | --- |
| doc_hit@1 / @3 / @5 | **0.95 / 1.00 / 1.00** |
| evidence_hit@1 / @3 / @5 | **0.90 / 0.95 / 0.95** |
| evidence_mrr | **0.925** |

两条未命中都留档在 `backend/evaluation/reports/corpus-eval-*.md`，原因清楚且不掩盖：

| 问题 | 现象 | 性质 |
| --- | --- | --- |
| 哪个项目是微服务版电商系统？ | 期望 `02-mall-swarm`，top1 是 `01-mall平台说明`（该文友情提示里也提到 mall-swarm） | 文档本身有重叠，属于真实歧义 |
| 精简版电商系统用了哪些技术？ | top1 文档是对的（`03-mall-tiny`），但证据词 `SpringBoot` 落在同文档的另一个分块里 | 切分粒度导致，@3 命中 |

标定过程中还修了两处标注问题（不影响代码，但影响指标可信度）：英文关键词改成大小写不敏感（语料写 `nacos`、标注写 `Nacos` 会误判未命中），以及把一条本身有歧义的问题换成唯一指向的问题。「评测标签不干净比没有评测更糟」这条也写进了经验。

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

### 阈值校准（两轮，都能复现）

第一轮（10 条示例语料，真实 BGE）：50 条相关问题最高余弦相似度最小值 0.374；8 条无关问题最大值 0.401 → 取 0.42 能挡 8/8 无关，但误伤 1 条相关问题（保留 49/50）。

第二轮（**当前语料**：5 篇公开资料 / 74 个分块，用 `backend/evaluation/calibrate_threshold.py` + `corpus_questions.json` 实测）：

| 分组 | 条数 | 最高余弦相似度 |
| --- | --- | --- |
| 域内问题（订单/物流/售后/快递条例） | 10 | 最低 **0.377**（"订单支付后多久发货？"） |
| 域外问题（天气/股票/做菜/编程等） | 8 | 最高 **0.360**（"Python 的装饰器怎么写？"） |

两组可分，中点 0.369。阈值-收益对比：

| 阈值 | 保留域内 | 挡下域外 |
| --- | --- | --- |
| 0.35 | 10/10 | 6/8 |
| **0.37（当前取值）** | **10/10** | **8/8** |
| 0.40 | 8/10 | 8/8 |
| 0.42（上一轮取值） | 8/10 | 8/8 |

结论：换语料后阈值必须重标，0.42 在新语料上会误伤 2 条域内问题；当前取 **0.37**。注意分离间隙只有 0.017（0.377 vs 0.360），比示例语料更窄——真实企业语料还要继续采样。

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

### Agent 任务评测（150 条，阶段 3 已完成）

一条命令：`cd backend && ..\.venv\Scripts\python.exe -m evaluation.agent_eval --tag full --use-real-embedder --offline`（约 18 秒跑完，默认不调用外部模型，**零 API 花费**；评测集构成 = 100 条新增 Agent 任务（订单 25 / 物流 15 / 政策 15 / 多轮 20 / 投诉转人工 13 / 拒答与注入 12）+ 50 条知识问答）。

| 指标 | 数值 |
| --- | --- |
| 任务成功率 | 99.33% |
| 路由 / 工具选择准确率 | 100.00% |
| 工具参数准确率 | 100.00% |
| 引用准确率 | 87.32% |
| 违规 / 幻觉率 | 0.00% |
| 转人工 Precision / Recall | 96.43% / 100.00% |
| 自动解决率 | 99.19% |
| 平均工具调用 / 平均重试 | 0.60 / 0.06 |
| P50 / P95 延迟 | 1 ms / 102 ms |

已知失败：`k38 积分有什么用？`（1/150）在阈值 0.42 下被判资料不足并转人工，属于阈值取舍的代价。报告留档在 `backend/evaluation/reports/`。

### 成本实测（真实模型，2026-09-19）

单价按 deepseek-flash 空闲时段官方价配置（输入 $0.15 / 百万 token、输出 $0.6 / 百万 token，高峰翻倍），跑 60 条核心集：

| 指标 | 实测 |
| --- | --- |
| 调用模型的次数 | 4 / 60（其余走 FAQ / 订单工具 / 转人工，不花钱） |
| 每次调用 token | 平均 230（示例语料很短） |
| 每次调用成本 | $0.000058（约 ¥0.0004） |
| 60 条任务总成本 | $0.000234 |

**换真实语料后的实测（2026-09-19，`evaluation/cost_report.py` 直接读 `data/logs/ask.jsonl`）**：18 次真实 RAG 调用，`top_k=5`：

| 指标 | 实测 |
| --- | --- |
| 每次调用 token | 平均 **1403**（输入 1321 + 输出 82） |
| 每次调用成本 | **$0.000247（约 ¥0.0018）** |
| 1000 次问答 | **$0.247（约 ¥1.8）** |
| 18 次调用总成本 | $0.00445 |

对比：示例语料时代每次只要 230 tokens / $0.000058，真实长文档的 prompt 大了 6 倍——**"上下文越长越贵"这件事有数字支撑，不是感觉**。同时注意 `/metrics` 里另有一条更重要的数字：1928 次调用中有 1910 次走的是 FAQ / 规则 / 本地工具，**完全没有调模型、成本为 0**，这也是"FAQ 优先"在成本上的意义。

复现命令：`cd backend && ..\.venv\Scripts\python.exe -m evaluation.cost_report`（单价读 `backend/.env`）。

### 生成质量评估（LLM-as-Judge，2026-09-19 实测）

命令：`python -m evaluation.generation_report --limit 150 --offline`（rubric 见 `app/judge.py`：1.0 / 0.5 / 0.0 三档）

| 指标 | 数值 |
| --- | --- |
| 参与评分（由模型基于资料生成） | 21 条 |
| 未参与评分（规则 / 工具路径） | 129 条：FAQ 41、订单工具 35、转人工 28、物流工具 25 |
| faithfulness 均值 | **1.00**（21 条里没有一条编造） |
| relevance 均值 | **0.929** |
| 低分条数（任一维度 < 0.6） | 3（14.29%） |

三条低分全部是"优惠券"主题（领取入口 / 有效期 / 适用范围）——知识库里确实没有这些内容，模型如实回复"暂时无法确认，建议联系人工客服"，因此 faithfulness 满分、relevance 半分。结论：**低分来自知识覆盖不足，不是模型幻觉**，这也正好说明为什么"导入真实资料"是当前第一优先级。

口径说明很重要：faithfulness 只对"依据资料生成"的答案有意义，FAQ 直答、工具直答、拒答与转人工属于规则路径，用转人工 Precision/Recall 等 Agent 指标衡量。第一版报告没做这个区分，把正确的转人工话术也扣成了低分，已修正。报告与人工复核抽样表都在 `backend/evaluation/reports/`。

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
- 知识版本与生效时间：`/ingest` 支持 `doc_key` / `version` / `effective_from` / `effective_to`；检索时同一 `doc_key` 只保留最高版本，超出时间窗口的片段不参与召回；`/ask` 传 `as_of` 可以回答「去年 8 月时政策是怎么规定的」这类问题（默认按今天）。
- 嵌入：`BAAI/bge-large-zh-v1.5`，`normalize_embeddings=True`，内积检索。
- 向量库：`VectorStore` 接口 + `FAISSVectorStore` 实现，元数据与索引分离落盘，重启可恢复。
- 关键词检索：`rank-bm25` + `jieba` 中文分词。
- 混合检索：向量与 BM25 融合，`top_k` 可传参（默认 5）。
- 多轮追问指代（`backend/app/followup.py`）：短问句（≤8 字）或以指代词开头（那/这个/它/还有…）时，检索词自动拼上上一轮用户问题——实测「寄贵重物品需要保价吗？」→「那丢了怎么赔？」，第二轮能正确接到保价与赔偿条款（引用第二十七条）。生成阶段仍只喂原始问题和对话历史，避免重复；`RAG_FOLLOWUP_MERGING=false` 可关闭。
- 可选 rerank：配置 `RERANK_MODEL` 后启用 BGE reranker。
- 生成：DeepSeek 客户端，支持普通与 SSE 流式两种调用。
- 兜底：检索不到可靠内容时返回「资料不足」而不是编造。

### 企业客服业务逻辑

- FAQ 优先命中：命中标准问题直接返回标准答案，不调用大模型。**例外语保护**：问题里出现定制/特殊/除外/生鲜/虚拟/预售/二手等限定词时不走 FAQ，改走检索——否则通用答案会盖掉知识库里的例外条款（可用 `FAQ_EXCEPTION_MARKERS` 自定义，写 `none` 关闭）。
- 意图路由：用规则识别投诉和明确的转人工请求，命中后跳过检索与生成；带防误判（「我不想转人工」不会触发）。
- 转人工统一出口 `escalate_to_human`：明确要求转人工、投诉、检索为空、相似度低于阈值、以及**模型自己说「资料里没有这条」**这五种情况都会建工单并返回带工单号的引导话术，`/ask` 与 `/ask/stream` 行为一致（`RAG_REFUSAL_MARKERS` 可配置识别词，写 `none` 关闭）。
- 低相关性兜底：`RAG_MIN_SCORE` 用原始余弦相似度做阈值（归一化分数永远有最大值 1.0，不能用它做绝对判断）；当前语料（5 篇公开资料 / 74 分块）标定值为 **0.37**（域内 10/10 保留、域外 8/8 挡下），默认 0 表示关闭，重标脚本见 `backend/evaluation/calibrate_threshold.py`。
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
- 评测分档：`--tag smoke|core|full`（25 / 60 / 150 条）与 `--limit`，日常只跑冒烟，里程碑跑全量并留档。
- 多轮指代（新增）：追问里没带订单号时，从最近几轮用户消息里取上一个订单号（「它的物流到哪了」），并在轨迹里记录 `resolve` 步骤与 `reused_from_history` 标记。
- 高风险写操作审批（新增）：`refund_request` 工具默认只创建审批单并返回 dry-run 预览，不执行任何写入；管理员通过 `GET /approvals` 查看、`POST /approvals/{id}/decision` 批准后才落地（本地 mock 只建单，不动真实资金）。审批带幂等键，重复批准不会重复执行；租户隔离。低风险的 `human_handoff` 仍然即时执行，不增加用户等待。
- 工具组合（新增）：同时问订单与物流时先调 `order_lookup` 再补 `logistics_track`，两段结果合成一条答案；步数上限（3 次业务调用）仍然生效，超限即降级。评测口径同步调整为「期望工具出现在成功调用的工具集合里即算命中」，150 条回归仍是路由 100%。
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

**状态：已完成（2026-09-19）**。过程中发现并修掉了一个阻塞性 bug（分块 id 撞车导致分数错位，见 `docs/FAILURE-CASES.md` 案例八）。

已做的：`backend/corpus/` 放了 5 篇**许可清晰**的公开资料（macrozheng/mall、mall-swarm、mall-tiny 的 Apache-2.0 平台说明，litemall 的 MIT 说明，《快递暂行条例》国务院令文本），共约 57 KB；用 `scripts/ingest-corpus.ps1` 导入 **74 个分块**；重新标定 `RAG_MIN_SCORE = 0.37`（见第 3 节）。

验证记录（容器内真实索引 + DeepSeek）：

| 提问 | 结果 |
| --- | --- |
| 快递签收时可以先验收吗？ | `deepseek-chat` 回答，引用《快递暂行条例》第二十五条「收件人有权当面验收」 |
| 订单支付后多久发货？ | FAQ 命中，零模型成本 |
| 今天北京的天气怎么样？ | 资料不足 → 转人工（工单号 T20260919C921D6） |
| 红烧肉怎么做才好吃？ | 资料不足 → 转人工（工单号 T2026091901027F） |

前端页面（`http://127.0.0.1:5173/`）实测：左侧来源面板显示 5 篇真实资料（含分块数），提问「快递签收时可以先验收吗？」返回引用《快递暂行条例》第二十五条的回答，引用可展开查看原文条款。另修掉一个部署坑：`web/nginx.conf` 原来在启动时只解析一次后端地址，重建后端容器后前端会静默回退到 mock 数据，现已改为 Docker DNS 动态解析（`resolver 127.0.0.11`）。

文件导入链路（`/ingest/file`）实测：上传一份带文字层的 PDF（内容为「定制商品不支持 7 天无理由退货」）→ 返回 `chunk_count=1` → 提问「定制商品可以无理由退货吗？」返回「定制商品**不支持** 7 天无理由退货，需要人工客服审批」并引用该 PDF。这条同时验证了 PDF 文本层解析和**例外条款不再被 FAQ 吞掉**（见 `docs/FAILURE-CASES.md` 案例九）。

拒答兜底实测（清空上传件后的干净索引）：问「定制商品可以无理由退货吗？」时，语料里确实没有这条规则，模型回答「无法确认……资料中未涉及」，系统自动补上「已为您转交人工客服跟进（工单号 T202609193742A5）」并把 `status` 标成 `insufficient`——**模型级拒答也有出口了**，不再是拿到一句「不知道」就没下文。

还没做的：真实**企业自有**资料（产品手册 / FAQ 表格 / 售后政策 PDF）仍未接入，仓库里是公开替代语料。

### P0-2 补齐项目说明文档

**状态：已完成（2026-09-19）。** `README.md`（是什么、怎么启动、接口、已知边界）和 `docs/RAG_DESIGN.md`（数据 / 切分 / Embedding / 向量库 / 检索 / Prompt / 评估 / 工程 / 数字汇总 / 已知不足，全部带实测数字与复现命令）都已就位。

**关于 `docs/ROADMAP.md`：刻意不建。** 路线图就是本文件第 5 节，再开一份单独文档只会出现两个版本的真相——这类重复文档迟早会不同步。

### P1-1 清理医学阶段遗留内容

**状态：已完成（2026-09-19）。** 示例语料与问题改成退货 / 发货 / 发票等客服样例；`backend/app/__init__.py` docstring 改为「企业智能客服后端应用包」；8 个测试文件里的医学示例文本（共 50 余处）批量替换为客服语义，并修正了因此不一致的断言。仓库内已无医学残留。

### P1-2 产出延迟与成本量化数字

已实测的部分：首 token 2.51 / 2.51 / 2.97 s，流式总耗时 2.64 / 2.69 / 3.13 s，单次查询 187 tokens（输入 153 + 输出 34）。剩下来要做的：在 `backend/.env` 填入 DeepSeek 单价（`DEEPSEEK_INPUT_PRICE_PER_MILLION`、`DEEPSEEK_OUTPUT_PRICE_PER_MILLION`），把 token 折算成金额并写进 `README.md`；样本量也要从 3 个问题扩到几十个。
涉及：`backend/.env`（本地，不提交）、`backend/app/cost.py`、`backend/data/logs/ask.jsonl`。

### P1-3 验证 rerank 的实际收益

**状态：已实测完成（2026-09-19），结论是「不开」。**

命令：

```bash
cd backend
..\.venv\Scripts\python.exe -m evaluation.corpus_eval --compare-rerank BAAI/bge-reranker-base
```

| 指标 | 不开重排 | 开重排（bge-reranker-base，CPU） | 变化 |
| --- | --- | --- | --- |
| doc_hit@1 | **0.95** | 0.85 | **−0.10** |
| evidence_hit@1 | **0.90** | 0.85 | −0.05 |
| evidence_hit@3 | 0.95 | 0.90 | −0.05 |
| evidence_mrr | **0.925** | 0.875 | −0.05 |
| 单次检索延迟 | **142 ms**（avg，含查询向量化） | — | — |
| 纯重排延迟（20 个候选） | — | **avg 6475 ms / p95 7633 ms / max 8928 ms** | — |

诊断细节（逐条对比 top1）：**5/20 条问题的 top1 被改掉，而且改坏的多**——例如把整段条款换成了 `cloud.macrozheng.com/start/...` 这样的 URL 碎片。原因推测有两个：一是本语料只有 74 个分块、一阶段命中已经很高（0.95），没有提升空间，重排只在噪声里挑；二是 CPU 上 278M 参数的 CrossEncoder 跑 20 个候选要 6.5 秒，对客服问答完全不可接受。

**决策：`RERANK_MODEL` 默认留空（关闭）。** 代码路径与 A/B 命令都保留——等语料规模上来、一阶段召回明显变弱（比如上千份文档、hit@1 掉到 0.8 以下）时再开着重测。对比逻辑本身用假重排器做了单测（`tests/test_corpus_eval_rerank.py`）。

### P2-1 代码规范与部署验证

**后端部分已完成（2026-09-19），前端 lint 仍未做。**

- 新增 `backend/ruff.toml`：只开"确定是问题"的规则（E4/E7/E9、F、I、UP、SIM、PERF、ISC、C4），刻意不做行宽与文档字符串强制，避免制造大面积风格 diff；`combine-as-imports` 保证带别名的导入不被拆成两段。
- 首次运行修掉 **58 处**自动可修问题（导入排序、过时写法、未使用导入含 `app/tools.py` 的 `field`、`app/vector_store.py` 里函数内未使用的 `faiss`）+ 手工修 7 处（隐式字符串拼接要加括号、`list.extend` 替代 append 循环、生效时间判断改成两个布尔量）。**现在 `ruff check .` 全绿**。
- 依赖放在 `backend/requirements-dev.txt`（生产镜像不变胖），CI 增加 Lint 步骤。
- `docker compose up --build` 真机验证已完成（见第 3 节 Docker 部署）。

仍未做：前端 ESLint / Prettier（需要装一批 npm 依赖）。
涉及：`backend/ruff.toml`、`backend/requirements-dev.txt`、`.github/workflows/ci.yml`。

### P2-2 扩充评估集

要做什么：把 50 条扩到 200 条左右，补上生成质量（faithfulness / relevance）报告，做成可重复运行的脚本。
涉及：`backend/evaluation/enterprise_eval.py`、`backend/evaluation/generation_eval.py`、`backend/app/judge.py`。

---

## 6. 已知问题与风险

- **索引里是公开替代语料，不是企业自有资料**：`backend/data/faiss/records.json` 目前 74 个分块（5 篇公开文档），检索与阈值指标基于这批语料；真实企业上线必须换成自己的手册/FAQ/售后政策并**重新标定阈值**。
- **阈值分离间隙很窄**：当前语料域内最低 0.377、域外最高 0.360，只差 0.017；语料再变就可能重叠。`backend/evaluation/calibrate_threshold.py` 在两组重叠时会直接报「无法分开」，不会给出假的安全值。
- ~~评估入口口径不一致~~ → 已修复：命令行默认注入真实模型（`--embedder bge`，可切 `hash` 做快速回归），测试替身只保留给单元测试；同时加 `--offline` 跳过联网校验（150 秒 → 17 秒）。
- **BM25 的 O(N²) 已修复**：新增 `BM25Index.scores()` 一次性打分，检索层改为单次调用（保留原 `score()` 签名）。512 条索引实测检索从平均 370.9 ms / P95 444.3 ms 降到 **187.5 ms / 193.4 ms**，结果与逐文档打分完全一致（有单测）。
- ~~成本数字缺失~~ → 已补：单价已配置在 `backend/.env`，`evaluation/cost_report.py` 可从日志算出单次成本（实测 $0.000247/次，1000 次 $0.247）。注意单次 RAG 成本随 prompt 长度线性变化，语料换大会同步变大。
- **rerank 实测为负收益，已默认关闭**：`bge-reranker-base` 在本语料上把 doc_hit@1 从 0.95 拉到 0.85，纯重排延迟 6.5 s/次（CPU、20 候选），所以 `RERANK_MODEL` 留空。详见第 5 节 P1-3。语料规模变大后应重新评估。
- **OCR 未实测**：只有钩子，扫描版 PDF 实际效果未知。
- **Docker 未实测构建**：文件齐全，但没有在本机跑过 `docker compose up`。
- ~~评估集偏小且偏理想~~ → 已补：真实语料上另做了一套 20 条标注评测（doc_hit@1 0.95 / evidence_hit@1 0.90 / evidence_mrr 0.925，见第 3 节）。但这两套加起来仍只有 70 条问题、5 篇资料，属于小型自建集，不能替代真实业务抽样。
- **相关性阈值跟着语料走**：当前 `RAG_MIN_SCORE=0.37` 是在 5 篇公开语料（74 分块）上标定的（域内最低 0.377、域外最高 0.360，间隔只有 0.017）。换成企业自有资料后必须用 `backend/evaluation/calibrate_threshold.py` 重新采样，否则会误拒答或漏拒答。
- **转人工只是“登记 + 话术”**：没有坐席排队、分配、实时会话，也没有转人工后的消息回流；工单目前只落盘成 JSON，可选 Webhook 外发。
- **没有 lint / format 脚本**，靠人工约定风格。
- **没有 README 和设计文档**，新人只能靠 `HANDOFF.md` + `PROGRESS.md`。
- ~~移动端只做过手动检查~~ → 已于 2026-09-19 做过一次自动化窄屏检查：用 CDP `Emulation.setDeviceMetricsOverride` 把视口压到 **375×800**，实测 `body.scrollWidth == 375`（**无横向溢出**），唯一"溢出"的元素是 `sr-only` 的无障碍标签（本身不可见）。来源面板、问答区、输入框、按钮在窄屏下都仍可访问。仍未做的是**跨浏览器/多机型的自动化回归**（需要引入 Playwright 之类的浏览器测试框架）。
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
..\.venv\Scripts\python.exe -m evaluation.corpus_eval          # 真实语料 20 条标注评测
..\.venv\Scripts\python.exe -m evaluation.calibrate_threshold  # 拒答阈值标定
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
