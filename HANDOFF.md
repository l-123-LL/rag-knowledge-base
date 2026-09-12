# 项目交接文档

> 本文档目标是让新的 AI 只阅读本文件和 `AGENTS.md` 就能接手项目，不依赖任何聊天记录。
> 未实现的决策会明确标注“计划”，避免误以为已经完成。

## 1. 项目目标

### 做什么

构建一个面向企业的智能客服问答系统：

- 从产品手册、FAQ、售后政策、物流规则等企业资料中检索内容。
- 使用本地向量检索与 DeepSeek 生成客服风格回答。
- FAQ 精确命中优先，未命中再走 RAG。
- 低置信度或敏感问题转人工客服。
- 不能泄露内部价格、客户隐私等敏感信息。

### 给谁用

- 主要用户：企业客户。
- 内部用户：客服人员、运营人员，用于维护知识库。
- 当前阶段使用者：开发者本人，用于验证客服问答流程。

### 成功标准

- 能导入产品 FAQ、手册、售后政策、物流规则等企业资料并建立索引。
- 能优先返回标准 FAQ 答案，未命中时基于企业资料生成客服回答。
- 无法可靠回答时，能建议转人工客服。
- 有可重复运行的测试集，能给出检索命中率、答案准确率、延迟和成本等量化指标。
- 所有改动都有 Git commit，且测试验证通过后才交付。

## 2. 当前进度

### 已完成

- 在项目根目录初始化 Git 仓库，当前分支为 `master`。
- 创建 `AGENTS.md`，约定提交和测试规则。
- 完成 `web/` 前端预览项目。
- 前端已能启动、构建、通过 TypeScript 类型检查。
- 前端包含左侧来源面板、右侧问答区、示例问答、引用折叠、空结果和错误状态。
- 关键前端代码已添加简短注释。
- 已加入 Vitest + React Testing Library，前端当前有 14 个测试并全部通过。
- 已建立前端 API 抽象层 `web/src/api/client.ts`，将 mock 问答集中到 API 模块。
- 已加入前端错误边界 `web/src/components/ErrorBoundary.tsx`，避免渲染异常导致白屏。
- 已创建 FastAPI 后端骨架，提供 `GET /health`、`POST /ask`、`GET /sources`。
- 前端 API 层会优先请求本地后端，后端不可用时自动回退到本地 mock。
- 前端来源面板已改为启动时请求 `/sources`，后端不可用时继续使用本地示例来源。
- 前端来源面板新增“上传资料”按钮，可上传 TXT、Markdown、HTML 和文本层 PDF。
- 前端来源面板新增网页 URL 输入框，可导入公开网页。
- 前端问答已接入 `/ask/stream`，答案会流式显示；不支持流式时自动回退到普通请求。
- 已实现文本切分、轻量混合检索、数据入口、DeepSeek 生成客户端和 RAG 管线模块。
- 已接入 `BAAI/bge-large-zh-v1.5` 嵌入模型、FAISS 向量库、jieba 分词和 rank-bm25。
- 后端 `/ask` 已切换到 RAG 管线，新增 `POST /ingest`，并支持文本层 PDF 解析。
- 新增 `POST /ingest/file`，支持上传 TXT、Markdown、HTML 和文本层 PDF。
- 新增 `POST /ingest/url`，可抓取公开网页、清洗正文并导入索引。
- 后端支持从 `backend/.env` 读取 `DEEPSEEK_API_KEY` 和 `HF_ENDPOINT`，示例见 `backend/.env.example`。
- 后端新增 `POST /ask/stream`，使用 SSE 流式返回 DeepSeek 生成内容。
- 检索流程已支持可选 rerank，通过环境变量 `RERANK_MODEL` 启用开源 BGE reranker。
- 前后端提示词、标题和示例数据已从医学方向切换为企业智能客服方向。
- `/ask` 已加入 FAQ 优先命中：匹配到标准问题时直接返回 FAQ 答案，不再调用大模型。
- `/ask` 已加入规则意图路由，可识别“投诉”和“转人工”并返回客服处理话术。
- 前后端已加入会话记忆：前端自动生成 `session_id`，后端保存最近对话并在生成时传入上下文。
- 前端新增“新会话”按钮，可清空当前对话并重置后端会话记忆。
- 问答请求会写入本地 JSONL 结构化日志，记录路由、模型、耗时、token、成本和引用数量。
- `/stats` 提供资料数、分片数、会话数和 FAQ 数，前端来源面板已展示这些统计。
- `/metrics` 从问答日志聚合查询量、平均延迟、总 token 和成本，前端已展示运行指标。
- 新增 `GET /faqs` 和 `POST /faqs`，支持运行时新增 FAQ 并立即参与优先命中。
- 前端来源面板已加入“新增 FAQ”表单，可直接录入问题、答案和关键词。
- 已加入后端、前端 Dockerfile 和 `docker-compose.yml`，可通过 Docker 启动完整服务。
- 已加入 GitHub Actions CI，推送或提交 PR 时自动跑后端测试、前端测试、类型检查和构建。
- 已用示例文本和真实 DeepSeek 完成一次端到端问答，返回了答案和引用。
- FAISS 在每次导入后保存到 `data/faiss`，重启后可恢复。
- 已加入检索评估指标和命令行运行器，示例评估结果为 `hit@1=1.0`、`MRR=1.0`。
- `/ask` 响应已加入 `latency_ms` 和 DeepSeek token 用量，便于后续计算延迟和成本。
- `/ask` 支持按环境变量配置的 DeepSeek 价格估算单次成本，未配置价格时返回 `null`。

### 已做到哪一步

已完成真实 RAG 最小闭环：

- 前端已能显示真实来源和真实问答结果。
- `/ask` 已接入 Embedding、FAISS、混合检索和 DeepSeek 生成。
- 已用示例文本完成一次真实端到端验证。
- 评估指标框架已建立，示例检索评估结果全命中。

### 尚未开始

- rerank。
- 扫描版 PDF OCR 和复杂表格解析。
- RAGAS 生成质量评估。
- 50 条以上正式评估集。
- 缓存、日志、监控。
- Docker 部署。

## 3. 文件地图

所有路径均为相对项目根目录的相对路径。

### 根目录

- `AGENTS.md`：项目强制规则，新 AI 必须先阅读。
- `HANDOFF.md`：本交接文档。

### 前端项目 `web/`

- `web/index.html`：HTML 入口，挂载 React 根节点。
- `web/package.json`：依赖、脚本和项目元信息。
- `web/package-lock.json`：锁定依赖版本，不应手工修改。
- `web/vite.config.js`：Vite 开发服务器配置，端口为 `5173`。
- `web/tailwind.config.js`：Tailwind 主题、颜色、圆角、字体和阴影令牌。
- `web/postcss.config.js`：Tailwind 与 Autoprefixer 的 PostCSS 配置。
- `web/tsconfig.json`：TypeScript 编译配置。
- `web/src/main.tsx`：React 应用真正入口文件，导入 `App` 和全局样式。
- `web/src/App.tsx`：应用骨架，组合来源面板、问答面板，并管理模拟问答状态。
- `web/src/types.ts`：`Source`、`Citation`、`Conversation`、`MockConversation` 等类型定义。
- `web/src/index.css`：Tailwind 基础样式、全局滚动条和字体规则。
- `web/src/styles.css`：前端自定义 `fade-in` 动画。
- `web/src/api/client.ts`：前端 API 抽象层，当前提供 mock 版 `askQuestion` 和 `listSources`。

### 前端数据与组件 `web/src/`

- `web/src/data/mockData.ts`：示例来源、示例问答、引用数据，以及本地关键词匹配函数 `findMockAnswer`。
- `web/src/components/App.tsx`：不存在，不要混淆；真正入口是 `web/src/App.tsx`。
- `web/src/components/SourcePanel.tsx`：左侧来源列表、来源状态和详情展开。
- `web/src/components/ChatPanel.tsx`：右侧问答主界面、空状态、消息列表和错误提示。
- `web/src/components/QuestionInput.tsx`：输入框、Enter 发送和发送按钮。
- `web/src/components/AnswerCard.tsx`：单个问答卡片，处理加载、答案、资料不足三种状态。
- `web/src/components/CitationList.tsx`：引用来源折叠/展开。
- `web/src/components/icons.tsx`：项目内使用的内联 SVG 图标组件。
- `web/src/components/ErrorBoundary.tsx`：渲染异常时的兜底页面。

### 入口文件

- 前端 HTML 入口：`web/index.html`
- 前端 JS 入口：`web/src/main.tsx`
- 后端入口：`backend/app/main.py`

### 后端项目 `backend/`

- `backend/requirements.txt`：FastAPI、Uvicorn、Pydantic、pytest、httpx 依赖。
- `backend/pytest.ini`：pytest 路径和测试目录配置。
- `backend/app/main.py`：FastAPI 应用入口和接口定义。
- `backend/app/schemas.py`：请求与响应的 Pydantic 数据模型。
- `backend/app/mock_data.py`：与前端一致的示例来源和示例问答。
- `backend/tests/test_api.py`：健康检查、问答、来源列表接口测试。
- `backend/app/factory.py`：真实 RAG 管线组装工厂。
- `backend/app/config.py`：加载 `backend/.env` 环境变量。
- `backend/.env.example`：本地环境变量示例，不提交真实 Key。
- `backend/app/chunking.py`：文本归一化和段落/窗口切分。
- `backend/app/embeddings.py`：Embedder 接口和测试用 HashEmbedder。
- `backend/app/vector_store.py`：内存向量库和 FAISS 向量库实现。
- `backend/app/retrieval.py`：jieba/rank-bm25、混合检索器和检索结果模型。
- `backend/app/ingestion.py`：TXT/Markdown/HTML 读取、清洗和文本层 PDF。
- `backend/app/generation.py`：DeepSeek 生成客户端。
- `backend/app/pipeline.py`：串联检索与生成的 RAGPipeline。
- `backend/app/reranker.py`：可选重排序器，默认使用 `BAAI/bge-reranker-v2-m3`。
- `backend/app/evaluation.py`：检索评估指标和批量运行函数。
- `backend/evaluation/run_eval.py`：示例评估命令行入口。
- `backend/evaluation/sample_corpus.json`：示例评估语料。
- `backend/evaluation/sample_questions.json`：示例评估问题。

## 4. 关键决策及原因

### 4.1 当前只做前端预览

**决策：** 先不实现后端，只做 React 前端原型。  
**原因：** 用户明确要求“只需要前端预览”“只需要能看就行”，优先快速看到界面效果，而不是先搭建重型 RAG 系统。

### 4.2 前端使用 React + Vite + TypeScript + Tailwind CSS

**决策：** 使用 React 18、Vite 5、TypeScript 5、Tailwind CSS 3。  
**原因：**

- Vite 启动快，适合本地预览。
- TypeScript 提供类型约束，后续接 API 时更安全。
- Tailwind 便于快速实现一致的浅色医疗风界面。

### 4.3 视觉采用“洁净浅色”

**决策：** 白底、蓝色主色、低饱和边框、清晰留白。  
**原因：** 面向客服场景，界面需要专业、可读、不花哨。

### 4.4 前端数据使用本地 mock，但保留未来 API 形状

**决策：** 把示例来源和问答放在 `web/src/data/mockData.ts`，组件通过 `Conversation` 等类型组织数据。  
**原因：** 方便先演示交互，后续把 `findMockAnswer` 替换为真实 `/ask` 请求时，UI 结构不需要大改。

### 4.5 后端技术方案为计划，尚未编码

当前已用 FastAPI 搭建后端骨架，但真实 RAG 能力尚未实现。以下是已讨论、但尚未实现的技术方向：

- 后端语言：Python 3.11+。
- 数据：官方公开指南/科普/说明书 + 用户合法自有资料。
- 切分：优先按标题/章节，块大小约 500–800 中文字符，重叠约 80 字符。
- Embedding：计划优先 `BAAI/bge-small-zh-v1.5`，维度 512。
- 向量库：计划优先 Chroma，本地持久化。
- 检索：计划使用向量检索 + BM25 混合，初步 `top_k=5`。
- 生成：计划调用 DeepSeek，模型 `deepseek-chat`。
- 评估：计划使用 RAGAS 指标 + 人工评测。

### 4.6 不使用图片生成工具

**决策：** 本次前端没有生成视觉稿。  
**原因：** 当前会话没有可用的图片生成工具，且用户只要“能看”的简单预览。

### 4.7 不在代码或文档中保存敏感信息

**决策：** API Key、密码等只保存在本地环境变量或未提交的 `.env` 文件中，绝不进入 Git。  
**原因：** 防止密钥泄露和误提交。

## 5. 下一步计划

按优先级排序：

### P0-1：补充前端自动化测试（已完成）

**状态：** 已完成，提交 `ea47fe9`。当前命令为 `cd web` 后运行 `npm test`。

**要做什么：**

- 在 `web/` 中引入 Vitest 和 React Testing Library。
- 给 `package.json` 增加测试脚本。
- 至少覆盖：
  - `findMockAnswer` 正确匹配和无匹配。
  - 引用列表展开/收起。
  - “资料不足”状态渲染。
  - 模拟错误状态渲染。

**涉及文件：**

- `web/package.json`
- `web/src/data/mockData.ts`
- `web/src/components/CitationList.tsx`
- `web/src/components/AnswerCard.tsx`
- `web/src/components/ChatPanel.tsx`

### P0-2：建立前端 API 抽象层（已完成）

**状态：** 已完成，提交 `bfde8e6`。`askQuestion` 和 `listSources` 已集中在 `web/src/api/client.ts`，错误边界已接入 `web/src/main.tsx`。

**要做什么：**

- 创建 `web/src/api/client.ts` 或类似模块。
- 定义 `askQuestion`、`listSources` 等函数。
- 保留 mock fallback，但把请求路径集中起来。
- 增加简单错误边界。

**涉及文件：**

- 新增 `web/src/api/client.ts`
- 新增 `web/src/components/ErrorBoundary.tsx`
- 修改 `web/src/App.tsx`
- 修改 `web/src/components/ChatPanel.tsx`

### P0-3：搭建 Python 后端骨架（已完成）

**状态：** 已完成，提交 `87a8e23`。后端提供三个 mock 接口，前端已通过 `/api` 代理尝试连接后端。

**要做什么：**

- 创建 `backend/` 目录。
- 使用 FastAPI 建立 `GET /health`、`POST /ask`、`GET /sources`。
- 先返回 mock 数据，验证前后端联通。

**涉及文件：**

- 新增 `backend/` 目录及入口文件
- 新增 `backend/requirements.txt` 或 `pyproject.toml`
- 修改 `web/src/api/client.ts`

### P0-4：实现最小 RAG 闭环（代码已完成，待真实联调）

**当前进度：** 核心模块已实现并通过测试，真实嵌入模型和 DeepSeek Key 尚未在本机完成实际联调。

**要做什么：**

- 导入少量官方 PDF 和网页。
- 完成清洗、切分。
- 使用 `bge-small-zh-v1.5` 生成向量。
- 写入 Chroma。
- 实现 BM25 + 向量检索。
- 调用 DeepSeek 生成并附引用。

**涉及文件：**

- 新增 `backend/` 下采集、解析、切分、索引、检索、生成模块。
- 新增测试数据目录。

### P1：评估与量化（进行中）

**当前进度：** 已实现检索命中率/MRR 评估和接口延迟/token 统计，尚未建立正式 50 条测试集和 RAGAS 生成质量评估。

**要做什么：**

- 建立 50 条左右医学问题测试集。
- 计算检索命中率、RAGAS faithfulness、context precision。
- 记录首 token 延迟和单次查询成本。

**涉及文件：**

- 新增 `evaluation/` 或 `backend/tests/evaluation/`

## 6. 已知问题与风险

### 核心功能缺失

- 当前没有真实 RAG，只有前端模拟问答。
- 已有 FastAPI 后端骨架，但仍没有真实 RAG 能力。
- 没有数据、Embedding、向量库、检索、生成和评估。

### 测试缺失

- 前端已补齐 Vitest 测试运行器、`npm test` 脚本和 14 个基础测试。
- 后端测试尚未开始，等后端骨架创建后再补 pytest。

### 文档缺失

- 没有 `README.md`。
- 没有 `docs/ROADMAP.md`。
- 没有 `docs/RAG_DESIGN.md`。

### 前端工程质量风险

- mock 数据和组件耦合较紧。
- 没有 lint、format 脚本。
- 没有 CI/CD。
- 移动端布局未经过自动化浏览器测试。
- 已有错误边界，但真实 API 异常路径尚未接入后端验证。

### 医学合规与安全风险

- 尚无隐私说明。
- 尚无来源授权和版本记录。
- 尚无危险症状、危重情况、用药剂量的风险拦截策略。
- 尚无“不能替代临床决策”的明确提示边界。

### 环境与密钥

- DeepSeek API Key 尚未配置。
- Key 应放在未提交的 `backend/.env`，参考 `backend/.env.example`。
- 项目虚拟环境 `.venv` 已创建，Python 版本为 3.12.14。

### 未验证部分

- 前端交互仅在浏览器手动验证过，没有自动化回归。
- 尚未验证真实 PDF 解析效果。
- 尚未验证 Chroma、BM25、Embedding 与 DeepSeek 的实际联调。
- 尚未下载 `BAAI/bge-large-zh-v1.5` 模型权重，首次查询会触发下载。
- 模型缓存已下载到 `D:\rag知识库\models\huggingface`，真实 DeepSeek Key 已用于验证 `/ask`。

## 7. 运行与验证方法

### 环境信息

当前机器已确认：

- Node.js：`v24.15.0`
- npm：`11.12.1`
- Git：`2.55.0.windows.5`
- Python：项目虚拟环境 `.venv`，版本 3.12.14。

### 启动前端

```bash
cd web
npm install
npm run dev -- --host 127.0.0.1
```

浏览器访问：

```text
http://127.0.0.1:5173/
```

### 类型检查

```bash
cd web
npm run typecheck
```

### 生产构建

```bash
cd web
npm run build
```

构建产物位于：

```text
web/dist/
```

### 预览生产构建

```bash
cd web
npm run preview
```

### 查看 Git 状态

```bash
git status --short --branch
git log --oneline --decorate --all
```

### 前端自动化测试

```bash
cd web
npm test
```

当前包含 6 个测试文件、14 个测试用例。

### 后端接口测试

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

当前包含 14 个后端测试，其中 4 个是 FastAPI 接口测试。

## 8. 不可违反的约束

### 提交规则

- 每次改动后必须创建对应的 Git commit。
- 每次改动后必须编写或更新相关测试。
- 在交付给用户前，所有测试和验证必须通过。

### 文件修改规则

- 删除、覆盖、移动或修改现有文件前，必须询问用户并说明后果，除非用户在当前对话中明确要求执行。
- 创建全新文件通常无需询问。

### 技术栈约束

- 前端必须保持 React + Vite + TypeScript + Tailwind CSS，除非用户明确要求更换。
- 后端计划使用 Python 3.11+，但该部分尚未开始。
- 不要擅自把前端改成 Vue、Angular 或静态 HTML 重构。

### 敏感信息约束

- 不要把 API Key、密码、token 写入代码、文档、日志或 Git。
- 未来 DeepSeek Key 只放在本地 `.env` 或环境变量中，并确保 `.env` 被 Git 忽略。

### 医学内容约束

- 回答必须尽可能附来源。
- 资料不足时必须明确拒答，不能编造医学结论。
- 对危险症状、危重情况、用药剂量等高风险问题必须保持审慎。

### 数据版权约束

- 只收录官方公开可下载资料和用户明确有权使用的资料。
- 不擅自抓取受版权保护的教材、期刊全文或需付费内容。

## 9. 待用户确认的问题

以下问题在继续开发前需要用户拍板：

- 首批导入哪些具体公开医学来源和 URL。
- 知识范围是“全科常见病”还是特定科室。
- 目标数据规模是多少份文档。
- 是否确认使用 DeepSeek 作为云端生成模型。
- DeepSeek API Key 是否已准备好，并希望放在哪个环境变量名。
- 后端先接真实接口，还是继续保持前端 mock。
- 最终运行形态是本地单机、局域网，还是云端部署。
- 是否需要登录、用户权限和访问控制。
- 测试集由谁提供，规模是 50 条还是更大。
- 检索命中率、答案准确率、延迟和成本的可接受阈值。
- 是否必须加入危险症状拦截和“不能替代临床决策”提示。
