# 阶段 0：最小改动升级方案

> 依据《社招_最小改动升级指令.md》与《社招_最小改动执行指令.md》。
> 本阶段只读文档与核心入口，未修改任何业务代码。
> 代码预算：新增 ≤12 文件、修改 ≤8 文件、净增 800–1200 行（不含测试与评测数据）。

---

## 1. 可复用的现有模块

| 模块 | 可复用的接口 | 用在哪 |
| --- | --- | --- |
| `backend/app/retrieval.py` | `HybridRetriever.search(query, top_k, exclude_sources, tenant_id)`、`RetrievedChunk`（含 `raw_dense_score`） | `knowledge_search` 工具直接包一层，不改内部 |
| `backend/app/pipeline.py` | `RAGPipeline.retrieve()` / `.answer()` / `.is_below_threshold()` | 工具工作流的知识检索与回退路径 |
| `backend/app/generation.py` | `DeepSeekGenerator.generate()` / `.stream()`、`GenerationResult`（含 usage） | 生成与 token 统计 |
| `backend/app/embeddings.py`、`vector_store.py` | `SentenceTransformerEmbedder`、`FAISSVectorStore` | 无需改动 |
| `backend/app/intent.py` | `classify_intent()` → `complaint` / `human` / `knowledge` | 工具路由的第一跳 |
| `backend/app/faq_store.py` | `find_faq_answer()` | FAQ 优先命中 |
| `backend/app/ticket_store.py` | `create_ticket(question, session_id, reason, tenant_id)` | `human_handoff` 工具直接调用 |
| `backend/app/session_store.py` | `get_history()` / `record_message()` | 多轮上下文 |
| `backend/app/tenant.py` | `get_tenant_id()` | 工具与 trace 的租户隔离 |
| `backend/app/observability.py` | `log_ask_event()`（JSONL 追加 + 可选 Webhook） | trace 记录复用同一套写入机制 |
| `backend/app/cost.py` | `calculate_cost(usage, input_price, output_price)` | 单任务成本 |
| `backend/app/security.py` | `require_admin_key` / `require_user_token` | 新增 trace 接口直接挂载 |
| `backend/app/evaluation.py` | `hit_at_k()` / `reciprocal_rank()` / `evaluate_retrieval()` | 评测规则评分底座 |
| `backend/evaluation/enterprise_eval.py` | `TOPICS`（10 主题 × 5 问法 = 50 条） | 扩充到 100 条的现有底座 |
| `backend/app/judge.py` | `DeepSeekJudge.score()` | LLM-as-Judge 辅助评分（抽样） |
| `backend/tests/`（17 文件 / 65 测试） | 现有回归基线 | 每次提交必须全绿 |
| 前端 `web/src/` | `api/client.ts`（已处理租户头与管理员 Key）、`App.tsx`、`ChatPanel`、`AnswerCard`、`CitationList`、`SourcePanel`、`types.ts` | 只加不重构 |

结论：核心链路全部可复用，新代码集中在"工具 + 状态机 + trace"三块。

---

## 2. 需要新增的文件（12 个，含测试与数据）

| # | 文件 | 作用 |
| --- | --- | --- |
| 1 | `backend/app/tools.py` | 工具注册表 + 3 个工具（`knowledge_search` / `order_lookup` / `human_handoff`），含 Pydantic 输入输出、统一错误码、超时与重试 |
| 2 | `backend/app/order_store.py` | 读取 mock 订单与物流数据的查询函数 |
| 3 | `backend/mock/orders.json` | mock 数据：20 条订单 + 10 条物流记录 |
| 4 | `backend/app/workflow.py` | 最小状态机：状态模型 + 路由 + 执行循环 + 降级 |
| 5 | `backend/app/trace_store.py` | trace 写入、按 `trace_id` 读取、PII 脱敏（脱敏并入本文件，避免多一个文件） |
| 6 | `backend/evaluation/agent_eval.py` | 100 条任务评测：规则评分 + 抽样 LLM 裁判 + JSON/Markdown 报告 |
| 7 | `backend/evaluation/agent_tasks.json` | 100 条任务数据（50 条现有 + 50 条新增） |
| 8 | `web/src/components/TraceTimeline.tsx` | Trace 时间线页面 |
| 9 | `README.md` | 项目说明：架构、可选工作流、评测命令、结果表、演示入口 |
| 10 | `backend/tests/test_tools.py` | 工具成功 / 参数错误 / 超时 / 重试 / 权限测试 |
| 11 | `backend/tests/test_workflow.py` | 状态流转、最大步数、降级、转人工测试 |
| 12 | `backend/tests/test_trace.py` | trace 读写、脱敏、查询接口测试 |

注意：mock 数据**不能放在 `data/`**，该目录已在 `.gitignore` 中；因此放在 `backend/mock/`。

---

## 3. 需要修改的现有文件（6 个）

| # | 文件 | 改动内容 | 兼容性 |
| --- | --- | --- | --- |
| 1 | `backend/app/schemas.py` | `AskRequest` 增加 `workflow_mode: Literal["rag","tools"] = "rag"`；`AskResponse` 增加可选 `trace_id`、`steps` | 默认值保证旧请求行为不变 |
| 2 | `backend/app/main.py` | `/ask` 与 `/ask/stream` 按 `workflow_mode` 分支；新增 `GET /traces/{trace_id}`（挂 `require_user_token`）；透传 `trace_id` | `rag` 分支代码路径完全不动 |
| 3 | `backend/.env.example` | 新增 `WORKFLOW_MODE_DEFAULT`、`TOOL_TIMEOUT_SECONDS=3`、`TOOL_MAX_RETRIES=1`、`WORKFLOW_TOTAL_TIMEOUT_SECONDS=15`、`TRACE_DIR` | 仅新增键 |
| 4 | `web/src/api/client.ts` | 新增 `getTrace(traceId)`；`askQuestion` / `streamAsk` 支持传 `workflow_mode` | 默认 `rag` |
| 5 | `web/src/types.ts` | 新增 `TraceStep`、`TraceRecord` 类型 | 仅新增 |
| 6 | `web/src/App.tsx` | 增加"工具工作流"开关与 Trace 入口（复用现有状态管理与视图切换） | 不动现有组件结构 |

（若开关放在输入区，可能小幅改动 `web/src/components/ChatPanel.tsx`，仍在 8 个文件预算内。）

---

## 4. 预计代码改动量

| 文件 | 行数 |
| --- | --- |
| `tools.py` | 240–280 |
| `order_store.py` | 60–80 |
| `workflow.py` | 150–190 |
| `trace_store.py`（含脱敏） | 100–130 |
| `agent_eval.py` | 200–260 |
| `TraceTimeline.tsx` | 120–160 |
| `schemas.py` / `main.py` / `client.ts` / `types.ts` / `App.tsx` / `.env.example` | 260–370（其中 `main.py` 120–160） |
| **合计** | **约 1,130–1,470** |

初版估算中位数约 1,300 行，**略超 1,200 上限**。三处收敛后可落到预算内：

1. `agent_eval.py` 复用现有 `evaluate_retrieval()`，评分层压到约 180 行；
2. `TraceTimeline.tsx` 只做只读时间线，不做筛选与图表，压到约 120 行；
3. `main.py` 的分支抽取成 `workflow.py` 内部函数，`main.py` 增量控制在 +120 行内。

收敛后合计约 **1,050–1,200 行**，符合预算。测试与数据不计入：测试约 400–600 行，mock 数据约 300 行 JSON，评测数据约 100 条。

---

## 5. 分阶段计划（2–3 周）

| 周 | 阶段 | 交付物 | 工时 | 验收 |
| --- | --- | --- | --- | --- |
| 第 1 周 | 阶段 1：工具与状态 | `tools.py`、`order_store.py`、`mock/orders.json`、`workflow.py`、`schemas.py`/`main.py` 分支、3 个工具测试 | 4–6 h | `workflow_mode="tools"` 走通 FAQ / 订单 / 转人工三条路径；`workflow_mode="rag"` 与升级前一致；65 个既有测试 + 新增测试全绿 |
| 第 2 周 | 阶段 2：Trace 与前端 | `trace_store.py`（含脱敏）、`GET /traces/{id}`、`TraceTimeline.tsx`、前端开关与入口 | 2–3 h | 任意一次任务能用 `trace_id` 还原：路由、工具、重试、token、成本、最终结果；日志中无手机号 / 邮箱 / 证件号 |
| 第 2–3 周 | 阶段 3：评测 | `agent_tasks.json`（100 条）、`agent_eval.py`、一命令报告 | 3–5 h | 一条命令输出 JSON + Markdown 报告；指标含 Task Success / Tool Selection / Tool Argument / Citation Accuracy / Handoff P&R / P50-P95 / token 与成本 / 重试率；结果留档 |
| 第 3 周 | 阶段 4：材料 | `README.md`、一页案例、三张截图、三个失败案例、五个面试问答 | 1.5–2 h | README 含新工作流、架构图、评测命令与结果表；三个失败案例可复现 |

合计 **12–18 小时**，按每周 5–8 小时投入正好落在 2–3 周。

---

## 6. 风险清单

| # | 风险 | 影响 | 缓解措施 | 怎么验证 |
| --- | --- | --- | --- | --- |
| 1 | 改 `main.py` 影响既有 20 个接口 | 回归风险高 | `workflow_mode` 默认 `rag`，旧分支代码路径不动 | 65 个既有测试全跑 + 对比升级前后 `/ask` 响应字段 |
| 2 | mock 数据误放 `data/` 被忽略 | 作品集缺数据 | 放 `backend/mock/`，README 说明 | `git status` 确认文件被跟踪 |
| 3 | trace JSONL 无限增长 | 磁盘与性能 | 按天分文件 + 单文件条数上限，文档说明 | 写入 100 条后检查文件切分 |
| 4 | 本地 mock 无法真实触发超时 | 超时重试测不到 | 注入可 sleep / 抛错的假工具 | 单测覆盖超时、重试、失败降级三条路径 |
| 5 | 50 条新评测任务需要人工定期望工具与参数 | 阻塞阶段 3 | 我起草全部条目，你复核（预计你 1–2 小时） | 复核后运行一次 baseline |
| 6 | 代码量超标 | 违反最小改动约束 | 第 4 节的收敛方案 | 每阶段提交前统计净增行数 |
| 7 | LLM-as-Judge 主观与成本 | 指标可信度 | 规则评分优先，裁判只做抽样辅助 | 对比规则分与裁判分的一致率 |
| 8 | 前端测试 jsdom 开销 | 拖慢每轮验证 | 纯逻辑测试用 node 环境，组件才用 jsdom | 记录分环境前后单轮耗时 |
| 9 | 模型选择（`deepseek-chat` vs `deepseek-flash`） | 延迟与成本差异 | 保持现有模型，另记录 flash 对比数据 | 同一批任务跑两种模型，记录延迟与 token |
| 10 | 与《总指令》大范围冲突 | 范围蔓延 | 已锚定最小改动版，超出部分一律记录为"下一阶段" | 阶段汇报里显式列出被推迟项 |

---

## 7. 本阶段不做

LangGraph / LangChain 重写、多 Agent、Redis / PostgreSQL / 消息队列、K8s、真实 CRM / 邮件 / 支付 / 退款 / 物流接入、150–200 条评测、独立监控平台、复杂长期记忆、新前端控制台、项目改名。

---

## 8. 待确认后进入阶段 1

确认本方案后，从阶段 1 开始实施：先落 `tools.py` + `order_store.py` + `workflow.py`，再接 `main.py` 分支，最后补测试。每完成一个文件即提交，保持可回滚。
