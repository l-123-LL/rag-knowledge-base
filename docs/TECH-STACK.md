# 技术栈、版本与流程图

> 数据来源：2026-10-17 在本机实际读取 `backend/.venv` 的包元数据、`web/package.json` 与
> `npm ls --depth=0`、两个 Dockerfile 的 `FROM` 行，以及仓库内代码文件统计。
> 版本分两种口径：**声明版本**（requirements.txt / package.json）与**实际安装版本**（本机 venv / node_modules）。

---

## 1. 语言构成

| 语言 / 文件类型 | 用途 | 文件数 | 行数（约） |
| --- | --- | ---: | ---: |
| **Python** | 后端全部业务逻辑、检索、评测、脚本 | 76 | 7,990 |
| **TypeScript / TSX** | 前端页面、组件、API 抽象层 | 26 | 2,703 |
| JavaScript | 前端构建配置（Vite / Tailwind / PostCSS） | 3 | 100 |
| CSS | 全局样式与设计令牌 | 2 | 148 |
| HTML | 前端入口页 | 1 | 13 |
| PowerShell | 一键启动、语料导入、Docker 修复脚本 | 3 | 176 |
| Markdown | 文档与语料 | 50 | 7,829 |
| YAML / JSON / Dockerfile / Nginx conf | 部署编排、CI、数据文件 | — | — |

主要开发语言是 **Python（后端）+ TypeScript（前端）**；PowerShell 只用于 Windows 本地脚本。

---

## 2. 后端技术栈

运行时：**Python 3.12.14**（虚拟环境 `.venv`）；容器基础镜像 `python:3.12-slim`。

| 类别 | 组件 | 实际安装版本 | 作用 |
| --- | --- | --- | --- |
| Web 框架 | FastAPI | **0.141.1** | 20+ 接口、依赖注入、自动生成 OpenAPI 文档 |
| ASGI 服务器 | Uvicorn | **0.52.4** | 运行 FastAPI，支持流式响应 |
| 数据校验 | Pydantic | **2.13.5** | 请求/响应模型与工具入参校验 |
| 向量模型 | sentence-transformers | **6.0.1** | 加载 `BAAI/bge-large-zh-v1.5`（1024 维） |
| 推理运行时 | torch | **2.14.0** | 模型推理（CPU） |
| 模型库 | transformers | **5.17.0** | sentence-transformers 的底层依赖 |
| 向量检索 | faiss-cpu | **1.15.0** | 本地精确内积检索（IndexFlatIP + IDMap2） |
| 关键词检索 | rank-bm25 | **0.2.2** | BM25 打分 |
| 中文分词 | jieba | **0.42.1** | BM25 的中文切词 |
| HTTP 客户端 | httpx | **0.28.1** | 调用 DeepSeek、网页导入、评测 |
| PDF 解析 | pypdf | **6.18.1** | 文本层提取 |
| PDF 表格 | pdfplumber | **0.11.10** | 表格抽取后转 Markdown |
| Excel 解析 | openpyxl | **3.1.5** | `.xlsx` 逐 sheet 转 Markdown 表格 |
| Word 解析 | python-docx | **1.2.0** | `.docx` 段落与表格按序提取 |
| 文件上传 | python-multipart | **0.0.32** | multipart/form-data |
| 鉴权 | PyJWT | **2.14.0** | 可选 OIDC/JWT 校验 |
| 测试 | pytest | **8.4.2** | 167 个后端用例 |
| 静态检查 | ruff | **0.16.8** | 代码检查（CI 中执行） |
| 数值计算 | numpy | **2.5.3** | 向量运算 |

生成模型：**DeepSeek `deepseek-chat`**，通过 OpenAI 兼容的 HTTP 接口调用（没有引入官方 SDK）。

---

## 3. 前端技术栈

运行时：**Node.js v24.15.0 / npm 11.12.1**；容器构建镜像 `node:24-alpine`，运行镜像 `nginx:1.27-alpine`。

| 类别 | 组件 | 声明版本 | 实际安装版本 |
| --- | --- | --- | --- |
| UI 框架 | React | `^18.3.1` | **18.3.1** |
| DOM 渲染 | react-dom | `^18.3.1` | **18.3.1** |
| 构建工具 | Vite | `^5.4.11` | **5.4.21** |
| React 插件 | @vitejs/plugin-react | `^4.3.4` | **4.7.0** |
| 语言 | TypeScript | `^5.6.3` | **5.9.3** |
| 样式框架 | Tailwind CSS | `^3.4.15` | **3.4.19** |
| CSS 处理 | PostCSS / Autoprefixer | `^8.4.49` / `^10.4.20` | 8.5.28 / 10.5.6 |
| 测试框架 | Vitest | `^2.1.9` | **2.1.9** |
| 组件测试 | @testing-library/react | `^16.3.3` | **16.3.3** |
| DOM 环境 | jsdom | `^25.0.1` | **25.0.1** |

前端没有用 UI 组件库（没有 Ant Design / MUI / shadcn），组件与设计令牌都是项目内自己实现的。

---

## 4. 技术栈总览

```mermaid
flowchart TB
    subgraph FE["前端 · TypeScript"]
        R["React 18.3.1"]
        V["Vite 5.4.21"]
        TS["TypeScript 5.9.3"]
        TW["Tailwind CSS 3.4.19"]
        VT["Vitest 2.1.9"]
    end
    subgraph BE["后端 · Python 3.12.14"]
        F["FastAPI 0.141.1"]
        UV["Uvicorn 0.52.4"]
        PD["Pydantic 2.13.5"]
    end
    subgraph AI["检索与生成"]
        ST["sentence-transformers 6.0.1"]
        BGE["BAAI/bge-large-zh-v1.5 · 1024 维"]
        FA["FAISS 1.15.0"]
        BM["rank-bm25 0.2.2 + jieba 0.42.1"]
        DS["DeepSeek deepseek-chat"]
    end
    subgraph PARSE["资料解析"]
        PDF["pypdf + pdfplumber"]
        OFFICE["openpyxl + python-docx"]
    end
    subgraph DEPLOY["部署"]
        PY["python:3.12-slim"]
        ND["node:24-alpine"]
        NG["nginx:1.27-alpine"]
    end
    FE -->|"HTTP /api"| BE
    BE --> AI
    BE --> PARSE
    DEPLOY -.-> FE
    DEPLOY -.-> BE
```

---

## 5. 工作流（代码执行路径）

对应 `backend/app/main.py` 的 `/ask` 接口。虚线分叉表示判定条件。

```mermaid
flowchart TD
    A["POST /ask"] --> B{"鉴权 + 租户识别"}
    B -->|"失败"| E401["401 / 403"]
    B -->|"通过"| C{"输入护栏"}
    C -->|"命中注入 / 密钥探测"| HO["建工单，转人工"]
    C -->|"通过"| D{"规则意图"}
    D -->|"投诉 / 明确要求转人工"| HO
    D -->|"知识类问题"| FAQQ{"FAQ 命中？"}
    FAQQ -->|"是"| FAQ["返回标准答案<br/>不调模型，成本为 0"]
    FAQQ -->|"否"| MODE{"workflow_mode"}
    MODE -->|"tools"| W["工具工作流<br/>最多 3 次工具调用，总超时 15s"]
    MODE -->|"rag，默认"| RET["混合检索<br/>BGE 向量 0.7 + BM25 0.3"]
    W --> WT{"工具类型"}
    WT -->|"只读"| QRY["查订单 / 查物流"]
    WT -->|"高风险写操作"| APPR["dry-run 预览 + 审批单"]
    RET --> TH{"最高原始余弦 ≥ 0.37？"}
    TH -->|"否"| HO
    TH -->|"是"| GEN["DeepSeek 生成<br/>回答 + 引用"]
    GEN --> REF{"模型自述资料不足？"}
    REF -->|"是"| HO
    REF -->|"否"| OUT["返回答案"]
    FAQ --> OUT
    QRY --> OUT
    APPR --> OUT
    HO --> OUT
    OUT --> LOG["记录会话 / 日志 / 执行轨迹"]
```

---

## 6. 业务流（客户视角）

```mermaid
flowchart LR
    U["客户提问"] --> K{"问题属于哪类？"}
    K -->|"标准问题"| FAQ["FAQ 直答"]
    K -->|"产品 / 政策知识"| RAG["RAG 检索并生成<br/>回答带引用"]
    K -->|"订单 / 物流"| TOOL["工具查询"]
    K -->|"退款等写操作"| AP["生成审批单"]
    K -->|"投诉 / 要求人工"| HO["转人工"]
    RAG -->|"资料不足"| HO
    FAQ --> C["客户看到答复"]
    RAG -->|"有可靠依据"| C
    TOOL --> C
    AP -->|"管理员批准"| C
    AP -->|"驳回"| HO
    HO --> TK["工单号 + 引导话术"]
```

---

## 7. 版本管理现状（需要注意的风险）

| 项目 | 现状 | 风险 |
| --- | --- | --- |
| 前端 | `package.json` 用 `^` 版本范围，但 `package-lock.json` 锁定实际版本，`npm ci` 可复现 | 低 |
| 后端 | `requirements.txt` 只写了 `>=` 下限，**没有 lock 文件**；本机装的是上表这些版本，但换台机器重装可能装到更新的版本 | **中**：FastAPI / Pydantic / torch 的大版本变化可能带来不兼容 |
| 模型 | `BAAI/bge-large-zh-v1.5` 权重缓存在 `models/huggingface`，未锁定 revision | 低（模型更新不频繁） |
| 容器 | `python:3.12-slim`、`node:24-alpine`、`nginx:1.27-alpine` 未固定到 digest | 低到中 |

建议：如需长期维护，补一份 `backend/requirements.lock`（`pip freeze > requirements.lock`）并在 Dockerfile 中安装 lock 文件，把版本风险降到和前端同一水平。

---

## 8. API 接口地图（22 个业务接口）

鉴权列的含义：**管理员 Key** = `X-API-Key`；**用户令牌** = 配置 OIDC 后才生效，未配置时放行；**租户头** = `X-Tenant-ID`。

| 分组 | 方法 | 路径 | 鉴权 | 用途 |
| --- | --- | --- | --- | --- |
| 健康与观测 | GET | `/health` | 无 | 健康检查（Docker healthcheck 用） |
| 健康与观测 | GET | `/stats` | 租户头 | 资料数 / 分块数 / FAQ / 工单 / 会话统计 |
| 健康与观测 | GET | `/metrics` | 无 | 查询量、平均延迟、token、成本、有帮助率 |
| 健康与观测 | GET | `/alerts` | 无 | 按延迟与有帮助率给出告警状态 |
| 健康与观测 | GET | `/traces/{trace_id}` | 租户头 + 用户令牌 | 按 trace_id 回放执行轨迹 |
| 问答 | POST | `/ask` | 租户头 + 用户令牌 | 同步问答（返回 answer / citations / usage / cost） |
| 问答 | POST | `/ask/stream` | 租户头 + 用户令牌 | SSE 流式问答 |
| 问答 | POST | `/feedback` | 租户头 | 有用 / 没用反馈 |
| 问答 | POST | `/session/reset` | 租户头 | 清空会话记忆 |
| 资料 | GET | `/sources` | 租户头 | 资料列表（从索引元数据反推） |
| 资料 | POST | `/ingest` | 租户头 + 管理员 Key | 直接导入纯文本 |
| 资料 | POST | `/ingest/file` | 租户头 + 管理员 Key | 上传文件导入（PDF/Word/Excel/CSV/HTML/MD） |
| 资料 | POST | `/ingest/url` | 租户头 + 管理员 Key | 抓取公开网页正文并导入 |
| 资料 | POST | `/sources/{source_id}/archive` | 租户头 + 管理员 Key | 停用 / 恢复某个来源 |
| FAQ | GET | `/faqs` | 租户头 | 列出 FAQ |
| FAQ | POST | `/faqs` | 租户头 + 管理员 Key | 新增 FAQ |
| FAQ | PUT | `/faqs/{faq_id}` | 租户头 + 管理员 Key | 修改 FAQ（版本号递增） |
| FAQ | DELETE | `/faqs/{faq_id}` | 租户头 + 管理员 Key | 删除 FAQ |
| 工单 | POST | `/tickets` | 租户头 | 创建工单（转人工时内部也会调用） |
| 工单 | GET | `/tickets` | 租户头 | 列出工单 |
| 审批 | GET | `/approvals` | 租户头 + 管理员 Key | 列出高风险操作审批单 |
| 审批 | POST | `/approvals/{approval_id}/decision` | 租户头 + 管理员 Key | 批准 / 驳回（幂等） |
| 运维 | POST | `/backup` | 管理员 Key | 打包备份数据目录 |

**鉴权现状（需要知道的风险）**：`/health`、`/metrics`、`/alerts` 完全公开；`/tickets` 与 `/feedback` 只需要租户头。单机演示没问题，**公网部署前必须补鉴权**，否则工单列表和指标是裸的。

---

## 9. 一次请求的时序（含耗时与失败点）

```mermaid
sequenceDiagram
    autonumber
    participant U as 浏览器
    participant N as Nginx / Vite
    participant A as FastAPI /ask
    participant R as HybridRetriever
    participant V as FAISS
    participant B as BM25 + jieba
    participant D as DeepSeek
    participant S as 本地存储

    U->>N: POST /ask {question, session_id, workflow_mode}
    N->>A: 转发请求
    A->>S: 读会话历史
    A->>A: 鉴权 / 租户 / 输入护栏 / 意图路由

    alt FAQ 命中
        A->>S: 读 FAQ
        A-->>U: 标准答案（实测 <100ms，零模型成本）
    else 走 RAG
        A->>R: 检索词（追问时合并上一轮问题）
        R->>R: BGE 编码查询
        R->>V: 向量检索
        R->>B: BM25 打分
        R-->>A: 归一化后按 0.7 / 0.3 融合
        Note over R,A: 检索整体约 100-150ms（74 分块、CPU、模型已加载）

        alt 最高原始余弦 < 0.37
            A->>S: 建工单
            A-->>U: 资料不足 + 工单号
        else 通过阈值
            A->>D: 提交 prompt（实测约 1400 tokens）
            D-->>A: 首 token 约 2.5-3.0s
            A-->>U: 流式返回答案 + 引用（总耗时约 2.6-3.1s）
        end
    end

    A->>S: 写 ask.jsonl 日志 + 执行轨迹（含 cost / trace_id）
```

耗时标注的口径：检索与 FAQ 是 2026-09 在本机 CPU 上的实测；首 token 与总耗时来自 3 次真实 DeepSeek 调用。**它们会随语料规模、网络和模型负载变化**，不是 SLA。
