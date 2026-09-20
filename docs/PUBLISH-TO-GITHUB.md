# 把项目发布到 GitHub

> **状态：已完成（2026-09-20）。** 仓库地址 <https://github.com/l-123-LL/rag-knowledge-base>，
> 136 个提交、177 个文件，CI（后端 ruff + pytest、前端 test + typecheck + build）两个 job 全绿。

## 一、网络现实（2026-09-19 实测）

**最终结论：** 直连不通时靠本机代理（`127.0.0.1:17890`，YunNiaoLoonCore）也能推成，但代理会间歇抖动；
真正决定成败的是**令牌权限**。实测踩到的两个坑值得记下来：

1. **细粒度令牌不好用**：`Contents: Read and write` 藏在权限行尾的下拉框里，很容易只选中 `No access`；
   而且它默认没有建仓库权限。最后改用**经典令牌勾 `repo`**，一次通过。
2. **有 `.github/workflows/` 的仓库，令牌必须额外勾 `workflow`**。否则 GitHub 会整次拒绝推送，
   报 `refusing to allow a Personal Access Token to create or update workflow ... without workflow scope`——
   注意是**整个推送被拒**，不是只跳过那个文件（表现为"177 个文件一个都没上去"）。
   经典令牌补勾 `workflow` 后**令牌字符串不变**，不需要重新复制粘贴。

| 目标 | 结果 |
| --- | --- |
| 直连 `github.com:443` / `ssh.github.com:443` / 备用 IP | 不通（TCP 超时） |
| 经本机代理 `127.0.0.1:17890` 访问 `github.com` | **通**（HTTP 200，8.8s） |
| 经代理访问 `api.github.com` | **通**（HTTP 200，1.3s） |
| 经代理 `git ls-remote https://github.com/cli/cli` | **通**（能列出分支） |
| `gitee.com` 直连 | 通 |

结论：**本机有个可用代理（127.0.0.1:17890）**，只是系统代理开关是关的。
git 单独指定代理后即可正常推送，所以走下面的路线 A。

---

## 二、发布前已经做完的检查

1. **密钥审计**：全仓库（含历史）搜索 `sk-*`、`DEEPSEEK_API_KEY=真实值`、`ADMIN_API_KEY=真实值`、`ghp_*`、`AKIA*`、邮箱、手机号。
   - `.env` 从未被提交过（历史里没有记录）；
   - 命中的都是文档里的占位符（`<你的 Key>`、`xxx`、`$VITE_ADMIN_API_KEY`）；
   - 唯一像邮箱/手机号的是 `backend/tests/test_trace.py` 里的假数据。
2. **不该公开的文件已移出跟踪**（文件仍保留在本地磁盘）：

   | 文件 | 原因 |
   | --- | --- |
   | `社招_*.md`（5 份） | 求职策略与执行指令，属于个人过程文档 |
   | `INTERVIEW.md` | 面试准备稿（含"面试官最爱""照着说"这类表述），公开等于把答案给面试官看 |

   需要重新纳入时：`git add -f INTERVIEW.md`。
3. **`.gitignore` 覆盖**：`.venv/`、`data/`、`models/`、`backend/.env`、`.github-token`、`backups/` 都不会进仓库。
4. **本地全量备份**：`backups/rag-knowledge-base-YYYYMMDD.bundle`（`git bundle` 单文件，含全部提交历史，可在任意机器 `git clone` 还原）。

---

## 三、路线 A：经本机代理直推（当前方案，保留完整提交历史）

### 一次性准备：设置令牌

```powershell
setx GITHUB_TOKEN "你的令牌"     # 设置后重开终端
```

也可以把令牌写进仓库根目录的 `.github-token`（已在 `.gitignore` 里，用完删掉）。
**不要**把令牌贴到聊天里，也不要写进任何会被提交的文件。

令牌权限：细粒度令牌需要 **Contents: Read and write** + **Administration: Read and write**（后者用于建仓库）；经典令牌勾 `repo`。

### 一条命令完成

```powershell
cd D:\rag知识库
.\.venv\Scripts\python.exe scripts\publish-to-github.py --repo rag-knowledge-base
```

脚本做的事：验证令牌 → 建仓库（已存在则复用）→ 用一次性 credential helper 推送。
令牌只经环境变量传给 git 子进程，**不会写进 `.git/config`，也不会出现在命令行**。

### 手动推送（等价的等价写法）

```powershell
git remote add origin https://github.com/<用户名>/rag-knowledge-base.git
git -c http.proxy=http://127.0.0.1:17890 -c https.proxy=http://127.0.0.1:17890 push -u origin master
```

这种方式会走 Git Credential Manager 弹窗认证；如果弹窗里的 GitHub 页面打不开（浏览器没走代理），就用上面脚本里的令牌方式。

---

## 四、路线 B：走 API 上传（不需要连 github.com，现在就能做）

前提：一个 GitHub 令牌（Personal Access Token）。

1. 在能访问 github.com 的设备上创建令牌：
   - 细粒度令牌：Repository permissions → **Contents: Read and write** + **Administration: Read and write**
   - 或经典令牌：勾选 `repo`
2. 在本机设置（**不要**贴进聊天，也不要写进任何会被提交的文件）：

   ```powershell
   setx GITHUB_TOKEN "你的令牌"
   ```

   设置后重开终端让新进程读到它。
3. 执行：

   ```powershell
   cd D:\rag知识库
   .\.venv\Scripts\python.exe scripts\publish-to-github.py --repo rag-knowledge-base
   # 私有仓库加 --private；只看计划不调接口加 --dry-run
   ```

   脚本会：创建仓库（已存在则复用）→ 逐个上传 blob → 建 tree → 建 commit → 建分支。

---

## 五、路线 C：Gitee 作为国内可达的镜像

`gitee.com` 直连可用，适合做异地备份或给国内面试官看：

```powershell
git remote add gitee https://gitee.com/<你的用户名>/rag-knowledge-base.git
git push -u gitee master
```

---

## 六、仓库建好后建议填的元信息

- **Description**：`企业智能客服 RAG/Agent 问答系统：BGE+FAISS+BM25 混合检索、工具工作流与人工审批、可观测与评测`
- **Topics**：`rag`、`fastapi`、`react`、`typescript`、`faiss`、`bm25`、`sentence-transformers`、`deepseek`、`customer-service`、`llm`
- **About → Website**：暂时留空（本地演示项目没有公网地址）
- 公开前再确认一次：仓库里没有 `.env`、没有真实订单/客户数据（当前索引与日志都在被忽略的 `data/` 下）

---

## 七、发布后要做的验证

1. 打开仓库首页，确认 README、架构图、截图能正常渲染。
2. 进入 Actions 页确认 CI 跑起来（`backend` 的 ruff + pytest、`frontend` 的 test/typecheck/build）。
   - 首次运行会装依赖，约 3–6 分钟；后端已改成先装 CPU 版 torch，避免拉 2GB 的 CUDA 依赖。
3. 把仓库地址贴回 `README.md` 顶部与简历里。
