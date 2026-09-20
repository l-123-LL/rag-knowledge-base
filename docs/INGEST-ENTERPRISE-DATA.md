# 接入企业自有资料（换掉公开语料）

> 现状：索引里是 5 篇公开许可资料（74 个分块），用来验证链路。这份文档说明**换成公司真实资料**的完整步骤。
> 全程只需要你准备文件 + 跑一条命令，剩下的（解析、切分、入库、重标阈值、重跑评测）我可以接手。

---

## 一、准备什么资料（按价值排序）

| 优先级 | 资料类型 | 典型格式 | 为什么值钱 |
| --- | --- | --- | --- |
| ★★★ | **售后/退换货政策** | PDF、Word | 客服最高频、也最容易答错（"能不能退""谁承担运费""时效多久"） |
| ★★★ | **FAQ 问答清单** | Excel、CSV | 一问一答的结构最适合做 FAQ 直答，命中后**零模型成本** |
| ★★☆ | **物流与时效规则** | Excel、PDF | 「发到新疆要几天」这类问题必须查表，模型自带知识不可信 |
| ★★☆ | **产品/服务手册** | Word、PDF | 长文档，靠父子切分保证答案不被切断 |
| ★☆☆ | **价格与优惠规则** | Excel | 数字敏感，错了就是资损 |

**够用就行**：先放 3–5 份最有代表性的（比如一份政策 PDF + 一份 FAQ 表 + 一份时效表），跑通再补。一次性丢几百份反而不好定位问题。

---

## 二、支持的格式

| 格式 | 处理方式 |
| --- | --- |
| `.md` / `.txt` | 直接按 UTF-8 读取，归一化空白 |
| `.html` / `.htm` | 去脚本样式与标签，反转义实体 |
| `.csv` | 转 **Markdown 表格**（保留表头，模型能读懂列含义） |
| `.xlsx` / `.xlsm` | 逐 sheet 转 Markdown 表格，sheet 名作为小节标题 |
| `.docx` | 按文档顺序取「段落 + 表格」，表格转 Markdown |
| `.pdf` | 取文本层；表格用 pdfplumber 抽出来转 Markdown 追加 |

**不支持 / 会失败的情况**：

- **扫描版 PDF**（整页是图片、没有文字层）—— 现在只有 OCR 钩子（`OCR_ENABLED=true`），未实测。这种资料请先自己 OCR 成文本或 Word。
- **加密文件**、`.doc`（老式二进制 Word，不是 `.docx`）—— 请另存为 `.docx`。
- **合并单元格特别复杂的表格** —— 转出来可能列对不齐，建议拆成规整表格。

---

## 三、放哪里：`backend/data/incoming/`

```text
D:\rag知识库\backend\data\incoming\      ← 把资料丢这里（可以带子文件夹）
```

这个目录**已被 `.gitignore` 忽略**，里面的资料不会进 Git、不会被推到 GitHub。

> ⚠️ **放进来的东西会进本地向量库**（`backend/data/faiss/`，同样被 gitignore）。
> 如果资料里有**真实客户姓名、手机号、订单号、身份证号**，请先脱敏再放——
> 索引一旦写入就很难逐条删干净（目前没有删除接口，只能整库重建）。

---

## 四、导入：一条命令

```powershell
cd D:\rag知识库
.\.venv\Scripts\python.exe scripts\ingest_folder.py
```

常用参数：

```powershell
# 换成别的目录
.\.venv\Scripts\python.exe scripts\ingest_folder.py --folder "D:\我的资料"

# 先看看会导入哪些文件，不真的调接口
.\.venv\Scripts\python.exe scripts\ingest_folder.py --dry-run
```

脚本会逐文件上传到 `/ingest/file`，打印每个文件新增的分块数；**单个文件失败不会中断整批**（扫描版 PDF 会在这里暴露出来）。

重复导入同一份资料会被**幂等跳过**（分块 id 里带内容哈希），所以不用怕多跑几次。

---

## 五、导入之后必须做的三件事（否则新资料答不出来）

这是最容易漏、也最坑的一步：**拒答阈值是跟着语料走的**。现在的 `RAG_MIN_SCORE=0.37` 是在公开语料上标的，换成公司资料后，同一个问题在新语料上的相似度可能只有 0.30，于是**明明有资料却判成"资料不足"转人工**。

### 1. 换掉标定用的问句

编辑 `backend/evaluation/corpus_questions.json`：

- `relevant`：**10 条**你的业务问题（必须是你资料里真能查到答案的）
- `unrelated`：**8 条**不该由知识库回答的问题（天气、股票、做菜之类）

> 这一步我可以代做：把资料给我，我按内容出 10 + 8 条候选问题，你过一眼改掉不合适的。

### 2. 重新标定阈值

```powershell
cd backend
..\.venv\Scripts\python.exe -m evaluation.calibrate_threshold
```

它会打印域内最低分、域外最高分和建议阈值。**如果两组分数重叠，脚本会直接说"分不开"**，不会给你一个假的安全值——那种情况说明语料或问题集需要调整。

### 3. 写回配置并重启

把新阈值写进 `backend/.env` 的 `RAG_MIN_SCORE`，然后：

```powershell
docker compose up -d --build backend      # 用 Docker 跑的
# 或用 start-backend.bat 重启本地后端
```

### 4. 复测（确认没退化）

```powershell
cd backend
..\.venv\Scripts\python.exe -m evaluation.corpus_eval        # 真实语料检索：doc_hit / evidence_hit / MRR
..\.venv\Scripts\python.exe -m evaluation.agent_eval --tag full --use-real-embedder --offline
..\.venv\Scripts\python.exe -m evaluation.cost_report        # 单次成本（prompt 变长会变贵）
```

换语料后 prompt 长度通常变化很大，**成本要重新看一遍**：公开语料 74 分块时实测 1403 tokens / $0.000247 每次，真实手册往往更长。

---

## 六、整库重建（想从头再来时）

没有删除单篇资料的接口，要清空就整库重建：

```powershell
cd D:\rag知识库
docker compose stop backend
Move-Item backend\data\faiss backend\data\faiss.backup-$(Get-Date -Format yyyyMMddHHmmss)
docker compose start backend
.\.venv\Scripts\python.exe scripts\ingest_folder.py       # 重新导入
```

（用 `Move-Item` 而不是删除：出问题时还能把旧索引换回来。）

---

## 七、几个实测经验

1. **FAQ 表比长文档更值钱**：一问一答的 CSV/Excel 命中后零模型成本、零延迟，而且答案可控。先把 FAQ 表喂进去，收益最大。
2. **表格一定要保留表头**：脚本转 Markdown 表格时会保留表头行，模型靠它理解「7 天」是"退货天数"还是"发货时效"。
3. **别把 FAQ 关键词设成通用词**：`订单`、`客服` 这种词单独命中会把无关问题吸走（真实踩坑：问「litemall 的商城功能里有没有订单售后」被答成发货时间）。代码里已经加了保护，但自己录 FAQ 时也尽量用具体词。
4. **政策类的例外条款要单独成段**：像「定制类商品除外」这种，如果和前文挤在一段里，切成两个分块后可能被拆散；单独一段反而更容易被检索到。
