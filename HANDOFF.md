# 项目交接文档

> 本文档目标是让新的 AI 只阅读本文件和 `AGENTS.md` 就能接手项目，不依赖任何聊天记录。
> 未实现的决策会明确标注“计划”，避免误以为已经完成。

## 1. 项目目标

### 做什么

构建一个面向医务人员的医学知识 RAG 智能问答系统：

- 从公开权威医学资料和用户合法自有资料中检索内容。
- 使用本地向量检索与云端大模型生成答案。
- 回答必须附来源，不能凭空生成。
- 先做前端预览，再逐步补齐后端 RAG 闭环。

### 给谁用

- 主要用户：医务人员。
- 当前阶段使用者：开发者本人，用于预览和验证界面。
- 未来可能扩展到本地单机使用或局域网团队使用。

### 成功标准

- 能导入至少一份官方医学资料并建立可检索索引。
- 能基于检索到的资料回答医学问题，并返回来源标题、URL、页码或章节。
- 检索不到足够依据时，明确回答“资料不足”，而不是编造。
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

### 已做到哪一步

目前只完成“前端可交互原型”：

- 问答使用本地示例数据模拟。
- 没有真实后端。
- 没有真实 RAG 能力。
- 没有数据、切分、Embedding、向量库、检索、生成、评估。

### 尚未开始

- Python 后端。
- 数据采集、清洗、解析。
- 文本切分。
- 中文 Embedding。
- Chroma 向量库。
- BM25 + 向量混合检索。
- rerank。
- DeepSeek 生成与引用校验。
- 自动化测试。
- 指标评估。
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

### 前端数据与组件 `web/src/`

- `web/src/data/mockData.ts`：示例来源、示例问答、引用数据，以及本地关键词匹配函数 `findMockAnswer`。
- `web/src/components/App.tsx`：不存在，不要混淆；真正入口是 `web/src/App.tsx`。
- `web/src/components/SourcePanel.tsx`：左侧来源列表、来源状态和详情展开。
- `web/src/components/ChatPanel.tsx`：右侧问答主界面、空状态、消息列表和错误提示。
- `web/src/components/QuestionInput.tsx`：输入框、Enter 发送和发送按钮。
- `web/src/components/AnswerCard.tsx`：单个问答卡片，处理加载、答案、资料不足三种状态。
- `web/src/components/CitationList.tsx`：引用来源折叠/展开。
- `web/src/components/icons.tsx`：项目内使用的内联 SVG 图标组件。

### 入口文件

- 前端 HTML 入口：`web/index.html`
- 前端 JS 入口：`web/src/main.tsx`
- 后端入口：尚未创建。

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

### 4.3 视觉采用“医疗洁净浅色”

**决策：** 白底、蓝色主色、低饱和边框、清晰留白。  
**原因：** 面向医学场景，界面需要专业、可读、不花哨。

### 4.4 前端数据使用本地 mock，但保留未来 API 形状

**决策：** 把示例来源和问答放在 `web/src/data/mockData.ts`，组件通过 `Conversation` 等类型组织数据。  
**原因：** 方便先演示交互，后续把 `findMockAnswer` 替换为真实 `/ask` 请求时，UI 结构不需要大改。

### 4.5 后端技术方案为计划，尚未编码

以下是已讨论、但尚未实现的技术方向：

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

### P0-1：补充前端自动化测试

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

### P0-2：建立前端 API 抽象层

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

### P0-3：搭建 Python 后端骨架

**要做什么：**

- 创建 `backend/` 目录。
- 使用 FastAPI 建立 `GET /health`、`POST /ask`、`GET /sources`。
- 先返回 mock 数据，验证前后端联通。

**涉及文件：**

- 新增 `backend/` 目录及入口文件
- 新增 `backend/requirements.txt` 或 `pyproject.toml`
- 修改 `web/src/api/client.ts`

### P0-4：实现最小 RAG 闭环

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

### P1：评估与量化

**要做什么：**

- 建立 50 条左右医学问题测试集。
- 计算检索命中率、RAGAS faithfulness、context precision。
- 记录首 token 延迟和单次查询成本。

**涉及文件：**

- 新增 `evaluation/` 或 `backend/tests/evaluation/`

## 6. 已知问题与风险

### 核心功能缺失

- 当前没有真实 RAG，只有前端模拟问答。
- 没有 Python 后端，电脑上当前也未检测到 Python 环境。
- 没有数据、Embedding、向量库、检索、生成和评估。

### 测试缺失

- 项目没有测试运行器。
- `package.json` 没有 `test` 脚本。
- 这与 `AGENTS.md` 第二条规定冲突，属于必须尽快修复的问题。

### 文档缺失

- 没有 `README.md`。
- 没有 `docs/ROADMAP.md`。
- 没有 `docs/RAG_DESIGN.md`。

### 前端工程质量风险

- mock 数据和组件耦合较紧。
- 没有 lint、format 脚本。
- 没有 CI/CD。
- 移动端布局未经过自动化浏览器测试。
- 没有错误边界，真实 API 异常时可能白屏。

### 医学合规与安全风险

- 尚无隐私说明。
- 尚无来源授权和版本记录。
- 尚无危险症状、危重情况、用药剂量的风险拦截策略。
- 尚无“不能替代临床决策”的明确提示边界。

### 环境与密钥

- DeepSeek API Key 尚未配置。
- 未来 Key 应放在未提交的本地 `.env` 或环境变量中。
- Python 环境尚未安装和验证。

### 未验证部分

- 前端交互仅在浏览器手动验证过，没有自动化回归。
- 尚未验证真实 PDF 解析效果。
- 尚未验证 Chroma、BM25、Embedding 与 DeepSeek 的实际联调。

## 7. 运行与验证方法

### 环境信息

当前机器已确认：

- Node.js：`v24.15.0`
- npm：`11.12.1`
- Git：`2.55.0.windows.5`
- Python：未检测到，需要先安装 3.11 或更高版本。

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

### 当前没有自动化测试

不要运行 `npm test`，因为该脚本尚未定义。

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

