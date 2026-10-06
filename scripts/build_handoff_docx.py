"""生成《rag交接文档.docx》——企业智能客服 RAG 系统交接文档（Word 版）。

用途：把交接文档做成可以直接发给同事的 Word 文件。仓库里的 `ONBOARDING.md` 是**持续维护的
Markdown 版本**，本脚本里的正文是它的 Word 排版版本——**两边内容需要同步维护**：改了
ONBOARDING.md 之后，记得同步改这里并重新生成，否则会出现两个版本的真相。

用法（仓库根目录）：
    .\\.venv\\Scripts\\python.exe scripts\\build_handoff_docx.py
    .\\.venv\\Scripts\\python.exe scripts\\build_handoff_docx.py --template "D:\\临时文档.docx" --out "D:\\rag交接文档.docx"

版式：如果传入 --template 且文件存在，就用它作为版式基底（保留页面设置与样式表，清空正文后重写），
这样和团队里已有的交接文档保持同一套字体与页边距；没有模板时从头创建，样式仍按本脚本设定。

注意：脚本用 python-docx，需要先装依赖（在虚拟环境里装饰即可）。
"""

import argparse
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "rag交接文档.docx"
ARCH_IMG = REPO_ROOT / "docs" / "architecture-modules.png"

HEADER_FILL = "1F3864"      # 表头深蓝
ROW_FILL = "F2F5FA"         # 隔行浅蓝灰
BORDER_COLOR = "D9D9D9"     # 浅灰边框
EA_FONT = "微软雅黑"


# ---------- 基础工具 ----------

def setup_styles(doc: Document) -> None:
    """统一字体与字号：正文 10.5pt、标题黑色（不跟随主题色）。"""
    normal = doc.styles["Normal"]
    normal.font.name = EA_FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.4

    for name, size, before, after in (
        ("Heading 1", 15, 18, 8),
        ("Heading 2", 12.5, 12, 6),
        ("Heading 3", 11, 10, 4),
    ):
        style = doc.styles[name]
        style.font.name = EA_FONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)

    title = doc.styles["Title"]
    title.font.name = EA_FONT
    title.font.size = Pt(24)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)


def para(doc, text, style=None, bold=False, size=None, space_after=None, align=None):
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    run.bold = bold
    run.font.name = EA_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
    if size:
        run.font.size = Pt(size)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    if align:
        p.alignment = align
    return p


def mono(doc, text):
    """命令行样式：等宽字体，不放进框里（避免文档出现成片的框）。"""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Consolas"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")
    run.font.size = Pt(9.5)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.22)
    return p


def bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(item)
        run.font.name = EA_FONT
        run._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
        run.font.size = Pt(10.5)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.35


def caption(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = EA_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(10)
    return p


def _set_cell_bg(cell, fill: str) -> None:
    cell._tc.get_or_add_tcPr().append(
        OxmlElement("w:shd") if False else _shd(fill)
    )


def _shd(fill: str):
    from docx.oxml import parse_xml

    return parse_xml(r'<w:shd {} w:val="clear" w:color="auto" w:fill="{}"/>'.format(nsdecls("w"), fill))


def _set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "6")
        el.set(qn("w:color"), BORDER_COLOR)
        borders.append(el)
    tbl_pr.append(borders)


def _cell_margins(table, top=80, bottom=80, left=110, right=110) -> None:
    tbl_pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for name, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{name}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tbl_pr.append(mar)


def table(doc, headers, rows, widths=None, font_size=9.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _set_table_borders(t)
    _cell_margins(t)

    for i, text in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(font_size)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.name = EA_FONT
        run._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
        cell._tc.get_or_add_tcPr().append(_shd(HEADER_FILL))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for r_index, row in enumerate(rows):
        cells = t.add_row().cells
        for c_index, text in enumerate(row):
            cell = cells[c_index]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(text))
            run.font.size = Pt(font_size)
            run.font.name = EA_FONT
            run._element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.25
            if r_index % 2 == 1:
                cell._tc.get_or_add_tcPr().append(_shd(ROW_FILL))

    if widths:
        for row in t.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def strip_body(doc: Document) -> None:
    """清空正文，保留 sectPr（沿用基底文档的页面设置）。"""
    body = doc.element.body
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)


# ---------- 正文 ----------

def build(template: Path | None, output: Path) -> None:
    if template and template.exists():
        doc = Document(str(template))
        print(f"使用版式基底：{template}")
    else:
        doc = Document()
        if template:
            print(f"提示：找不到模板 {template}，改为从头创建")
    strip_body(doc)
    setup_styles(doc)

    doc.add_paragraph("交接文档", style="Title")
    para(
        doc,
        "企业智能客服 RAG 系统 项目交付与部署说明",
        size=12,
        space_after=10,
    )
    para(
        doc,
        "这份文档写给接手本项目的工程师。它说明项目是什么、当前做到哪一步、怎么在本机跑起来、"
        "代码在哪里改、有哪些已知限制，以及接手后建议优先做什么。文中的状态与数字来自 2026-10-06 "
        "在本机的实际运行验证；引用历史结论但当天未复验的地方，以及尚未验证的部分，都单独标注。",
    )

    # 1
    doc.add_heading("1 这个项目是什么", level=1)
    para(
        doc,
        "这是一个面向企业的智能客服系统。顾客的提问先经过规则层，再按两条链路处理："
        "知识类问题走 RAG，从产品手册、FAQ、售后与物流政策中检索，再用 DeepSeek 生成带引用的回答；"
        "业务类问题走工具调用，可以查订单、查物流、发起退款。查不到资料、或涉及高风险写操作时，"
        "系统会拒答并转人工，而不是编造答案。",
    )
    para(
        doc,
        "它的设计目标不是做一个能聊天的演示页面，而是把客服场景里几个必须守住的边界做出来："
        "回答必须能追溯到原文、资料不足要有出口、动钱的操作必须人工批准、每次执行都能复盘。",
    )

    # 2
    doc.add_heading("2 项目定位与当前状态", level=1)
    para(
        doc,
        "项目目前处于可演示、可评测、可继续开发的阶段。业务数据全部是本地模拟数据，"
        "知识库用的是公开许可资料，因此它可以作为技术验证和面试材料，但不能直接上线。",
    )
    table(
        doc,
        ["项目", "当前信息"],
        [
            ["项目名称", "企业智能客服 RAG / Agent 问答系统"],
            ["代码路径", r"D:\rag知识库"],
            ["远程仓库", "https://github.com/l-123-LL/rag-knowledge-base（142 个提交，CI 全绿）"],
            ["技术栈", "后端 FastAPI + FAISS + BM25 + BGE 中文向量；前端 React + Vite + TypeScript + Tailwind"],
            ["生成模型", "DeepSeek deepseek-chat（Key 在 backend/.env，未进 Git）"],
            ["知识库规模", "5 篇公开许可语料，74 个分块（2026-10-06 实测）"],
            ["测试状态", "后端 167 个用例 + ruff 全绿；前端 31 个用例 + 类型检查通过"],
            ["已知边界", "业务数据为本地 mock；无鉴权默认关闭；Docker 在本机不稳定"],
        ],
        widths=[1.3, 5.2],
    )
    caption(doc, "表 1 项目当前信息")

    # 3
    doc.add_heading("3 系统架构", level=1)
    para(
        doc,
        "系统分五层。前端只负责展示与交互；接口层统一收口鉴权、限流与租户识别；"
        "编排层是核心，它决定一次提问走哪条链路；检索与生成层负责具体的检索、排序与答题；"
        "存储层把向量索引、业务记录和外部依赖分开。",
    )
    table(
        doc,
        ["分层", "职责", "主要文件"],
        [
            ["前端", "用户视图与管理视图、引用展示、执行轨迹、审批面板", "web/src/（App.tsx 与 9 个组件）"],
            ["接口层", "20+ 接口、请求校验、鉴权、限流、租户识别", "backend/app/main.py、schemas.py"],
            ["编排层", "RAG 链路与工具工作流、规则意图、拒答判定", "pipeline.py、workflow.py、intent.py、refusal.py"],
            ["检索与生成", "切分、向量化、混合检索、重排、提示词与流式输出", "chunking.py、embeddings.py、retrieval.py、generation.py"],
            ["存储层", "向量索引与元数据、FAQ、工单、审批、会话、日志", "vector_store.py、*_store.py、backend/data/"],
        ],
        widths=[0.9, 2.9, 2.7],
    )
    caption(doc, "表 2 分层职责")

    if ARCH_IMG.exists():
        pic = doc.add_paragraph()
        pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic.add_run().add_picture(str(ARCH_IMG), width=Inches(6.1))
        caption(doc, "图 1 模块划分图")

    doc.add_heading("3.1 一次提问的完整链路", level=2)
    para(
        doc,
        "理解这个项目最快的方式是跟着一次提问走一遍。下面这条链路对应 backend/app/main.py 的 /ask 接口。",
    )
    bullets(
        doc,
        [
            "租户识别与鉴权：从请求头读取租户，按配置校验管理员 Key 或 OIDC 令牌。",
            "输入护栏：命中提示词注入、密钥探测、跨租户尝试等模式时直接转人工，不进入检索与生成。",
            "规则意图：投诉或明确要求转人工的请求，直接建工单并返回带工单号的话术。",
            "FAQ 命中：命中标准问题则直接返回标准答案，不调用模型、不做检索，成本为零。",
            "模式分流：请求指定 tools 时进入工具工作流（最多 3 次业务工具调用，总超时 15 秒），否则走 RAG。",
            "RAG 检索：混合检索（向量 0.7 / BM25 0.3），按租户、停用来源、生效时间与知识版本过滤。",
            "阈值判定：最高原始余弦相似度低于 RAG_MIN_SCORE 时判定资料不足，转人工。",
            "生成：把命中的片段交给 DeepSeek 生成回答，支持流式输出，回答附带可展开的引用。",
            "拒答识别：模型自述资料不足时，保留它的解释并补一句带工单号的转人工话术。",
            "留痕：记录会话记忆、结构化日志（路由、模型、延迟、token、成本）与执行轨迹。",
        ],
    )
    para(
        doc,
        "三条答不出来的路径全都有出口：检索为空、相似度低于阈值、模型自己说资料里没有。"
        "这三种情况都会建工单并返回工单号，而不是把用户卡在一句无法确认上。",
    )

    doc.add_heading("3.2 文件目录", level=2)
    table(
        doc,
        ["路径", "用途"],
        [
            ["backend/app/", "后端全部业务模块（30 个文件，约 3800 行）"],
            ["backend/corpus/", "公开许可的演示语料（进 Git）"],
            ["backend/mock/orders.json", "本地模拟订单与物流（进 Git）"],
            ["backend/data/", "运行时数据：向量索引、日志、轨迹、审批、工单、会话、FAQ（不进 Git）"],
            ["backend/evaluation/", "四套评测、阈值标定、成本报告、压测脚本与报告留档"],
            ["backend/tests/", "后端测试（167 个用例）"],
            ["web/src/", "前端源码：页面骨架、9 个组件、API 抽象层"],
            ["web/.env", "前端配置：决定 5173 是管理视图还是用户视图（不进 Git）"],
            ["docs/", "设计说明、部署、故障复盘、演示脚本等文档"],
            ["models/huggingface/", "BGE 模型权重缓存（不进 Git，删除后需重新下载）"],
            ["scripts/", "一键演示、语料导入、GitHub 发布、Docker 修复脚本"],
        ],
        widths=[1.9, 4.6],
    )
    caption(doc, "表 3 目录结构与用途")

    # 4
    doc.add_heading("4 快速上手手册", level=1)
    doc.add_heading("4.1 访问地址", level=2)
    table(
        doc,
        ["服务", "地址", "说明"],
        [
            ["管理端前端", "http://127.0.0.1:5173", "资料管理、FAQ、审批面板、执行轨迹"],
            ["用户端前端", "http://127.0.0.1:5174", "客户视角，只有问答与转人工"],
            ["后端接口", "http://127.0.0.1:8000", "接口文档见 /docs"],
            ["健康检查", "http://127.0.0.1:8000/health", "返回 {\"status\":\"ok\"}"],
        ],
        widths=[1.3, 2.2, 3.0],
    )
    caption(doc, "表 4 本地服务地址")

    doc.add_heading("4.2 启动顺序", level=2)
    para(doc, "本地开发模式（推荐，改代码用这个），双击项目根目录的脚本：")
    mono(doc, r"start-all.bat")
    para(doc, "它会打开三个窗口：后端 8000、管理端 5173、用户端 5174。")
    para(doc, "Docker 模式（给别人演示用）：")
    mono(doc, r"powershell -ExecutionPolicy Bypass -File scripts\demo.ps1")
    para(
        doc,
        "注意：Docker 镜像默认不内联管理员 Key，所以容器版的 5173 是用户视图，看不到审批面板。"
        "需要在容器里看管理端，要用 --build-arg VITE_ADMIN_API_KEY 重新构建前端镜像。",
    )
    para(doc, "只跑后端（调接口或跑评测时）：")
    mono(doc, r"cd backend")
    mono(doc, r"..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
    para(
        doc,
        "首次启动的耗时要心里有数：后端接口就绪只要 3 到 5 秒，但模型还没加载；"
        "第一次走 RAG 的请求需要 10 到 20 秒（加载 BGE 权重约 11 秒），之后每次检索约 100 毫秒；"
        "FAQ 请求一直很快，因为它既不检索也不调用模型。",
    )

    doc.add_heading("4.3 停止方式", level=2)
    para(doc, "本地模式直接关闭那三个命令行窗口即可。Docker 模式：")
    mono(doc, r"docker compose stop          # 保留容器与数据")
    mono(doc, r"docker desktop stop          # 干净关闭引擎，避免 socket 卡死")
    para(
        doc,
        "不要用 docker compose down -v，那会删除数据卷。也不要直接强杀 Docker 进程，"
        "很容易留下无法清理的 socket 文件（见第 9 节）。",
    )

    doc.add_heading("4.4 五分钟验证清单", level=2)
    para(doc, "接手后先跑这五条，对不上说明环境有问题。以下数字是 2026-10-06 的实测结果。")
    mono(doc, r"curl.exe http://127.0.0.1:8000/health          # 期望 {\"status\":\"ok\"}")
    mono(doc, r"curl.exe http://127.0.0.1:8000/stats           # 期望 chunk_count=74, source_count=5")
    mono(doc, r"cd backend && ..\.venv\Scripts\python.exe -m pytest   # 期望 167 passed")
    mono(doc, r"..\.venv\Scripts\python.exe -m ruff check .           # 期望 All checks passed")
    mono(doc, r"cd ..\web && npm test && npm run typecheck            # 期望 31 passed，类型检查无输出")

    # 5
    doc.add_heading("5 密钥文件与敏感信息", level=1)
    para(
        doc,
        "所有密钥只存在本机的环境文件里，不写进代码、文档或日志。下面说明每个密钥放在哪、"
        "谁需要知道、什么时候要改。具体值请从现有环境文件读取，不要复制到任何文档或聊天记录中。",
    )
    table(
        doc,
        ["项目", "位置", "说明"],
        [
            ["DeepSeek API Key", "backend/.env 的 DEEPSEEK_API_KEY", "生成模型调用凭证，计费账号；单次问答约 0.0002 美元"],
            ["管理端 Key", "backend/.env 与 web/.env 各一份（两处必须一致）", "轮换时两处同时改，并重建前端"],
            ["GitHub 凭据", "Windows 凭据管理器（git:https://github.com）", "经典令牌，需要 repo 与 workflow 两个权限"],
            ["数据库/外部系统", "暂无", "当前未接真实订单、CRM 或支付系统"],
            ["运行时数据", "backend/data/", "索引、日志、工单、审批记录，全部不进 Git"],
        ],
        widths=[1.4, 2.5, 2.6],
    )
    caption(doc, "表 5 密钥与敏感信息位置")
    bullets(
        doc,
        [
            "backend/.env 与 web/.env 都在 .gitignore 里，仓库中只有不含密钥的 .env.example 模板。",
            (
                "个人材料（面试准备稿、投递记录、学习手册）虽然物理上在项目目录内，"
                "但已被 .gitignore 排除；更安全的做法是移出项目目录，避免将来误提交。"
            ),
        ],
    )

    # 6
    doc.add_heading("6 知识库交接", level=1)
    para(
        doc,
        "知识库支持 Markdown、TXT、HTML、CSV、Excel、Word 和带文字层的 PDF。"
        "解析时表格会转成 Markdown 保留表头，Word 按原文顺序取出段落与表格。",
    )
    table(
        doc,
        ["项目", "现状"],
        [
            ["当前语料", "backend/corpus/ 下 5 篇公开许可资料：两个电商平台说明、一个精简版说明、一个 MIT 许可说明、《快递暂行条例》"],
            ["分块规模", "74 个分块（每篇 9 到 18 块不等）"],
            ["切分策略", "按段落优先聚合，超长段落再开 80 字重叠窗口；可选父子切分（子块 400 字检索、父块 1200 字生成）"],
            ["导入方式", "资料放进 backend/data/incoming/，执行 scripts/ingest_folder.py；重复导入按内容哈希幂等跳过"],
            ["分块标识", "来源 + 序号 + 内容哈希，保证全局唯一，避免多篇资料 id 撞车"],
            ["知识版本", "支持 doc_key、version、effective_from/to；检索时同 doc_key 只取最高版本，可按历史日期检索"],
            ["拒答阈值", "RAG_MIN_SCORE=0.37，用原始余弦相似度判断，换语料后必须重新标定"],
        ],
        widths=[1.3, 5.2],
    )
    caption(doc, "表 6 知识库现状")
    para(
        doc,
        "换语料后必须重新标定阈值，这是最容易漏的一步。漏掉的后果是：明明有资料，"
        "却因为相似度低于旧阈值被判定资料不足、转人工。标定方法见 docs/INGEST-ENTERPRISE-DATA.md，"
        "命令是 backend/evaluation/calibrate_threshold.py；当两组分数重叠时脚本会直接报分不开，"
        "不会给出一个看似安全的假值。",
    )

    # 7
    doc.add_heading("7 外部系统依赖", level=1)
    table(
        doc,
        ["系统", "当前状态", "说明"],
        [
            ["DeepSeek API", "已接入并验证", "生成回答，Key 在 backend/.env；网络受限时生成会失败并返回 503"],
            ["HuggingFace", "仅需首次下载权重", "权重已缓存在 models/huggingface；运行时应开启离线模式，否则首次请求会卡几十秒"],
            ["GitHub", "已接入", "仓库与 CI；本机直连不通，需要代理才能 push"],
            ["订单与物流", "本地 mock", "backend/mock/orders.json，20 条订单与 10 条物流，接真实系统时替换 order_store.py"],
            ["工单与审批", "本地文件", "落盘在 backend/data/，可选 Webhook 外发到外部系统"],
            ["Docker", "可选", "用于演示与部署验证；本机不稳定，日常开发建议用本地模式"],
        ],
        widths=[1.3, 1.5, 3.7],
    )
    caption(doc, "表 7 外部依赖与当前状态")

    # 8
    doc.add_heading("8 开发规范", level=1)
    bullets(
        doc,
        [
            "每次改动都要有对应的 Git commit，交付前所有测试必须通过（项目根目录 AGENTS.md 的强制要求）。",
            "改后端代码后跑 pytest 与 ruff check；改前端后跑 npm test、npm run typecheck、npm run build。",
            "新增功能要补测试：本项目已有 167 个后端用例与 31 个前端用例，沿用同样的写法。",
            "任何 Key、密码、令牌都不能写进代码、文档、日志或提交记录。",
            "评测相关的数字要能复现：对外引用前先跑一遍对应命令，并把结果写进 PROGRESS.md。",
            "提交信息用中文或英文描述改了什么以及为什么，不要写 update 这类无信息的提交。",
        ],
    )

    # 9
    doc.add_heading("9 已知问题与环境限制", level=1)
    para(doc, "这些问题都已确认存在，接手前需要知道。状态栏区分了已解决、未解决与未验证。")
    table(
        doc,
        ["问题", "状态", "影响与建议"],
        [
            ["语料是公开替代资料，不是企业真实资料", "未解决", "指标只代表当前语料；换成真实资料后必须重标阈值"],
            ["拒答阈值分离间隙窄（0.377 与 0.360 只差 0.017）", "已知", "语料变动可能导致两组分数重叠，届时需调整语料或问题集"],
            ["rerank 实测为负收益（命中率 0.95 降到 0.85）", "已决策关闭", "这是当前语料规模的结论，不是重排无用；语料变大后应复测"],
            ["业务数据是本地 mock", "未解决", "工具执行只建本地单，不触达真实资金与订单"],
            ["转人工只到建工单与话术", "未实现", "没有坐席排队、分配、实时会话与消息回流"],
            ["扫描版 PDF 的 OCR 未实测", "未验证", "此类资料请先自行转成 Word 或文本再导入"],
            ["默认无鉴权", "已知", "公网部署前必须补鉴权，否则导入与审批接口是裸的"],
            ["Docker Desktop 在本机不稳定", "环境问题", "异常退出后会残留 socket 导致启动失败，用 scripts/fix-docker-socket.ps1 修复"],
            ["GitHub 直连不通", "环境问题", "需要代理；推送失败先重试，代理会间歇抖动"],
            ["前端没有 ESLint 与 Prettier", "未做", "后端已有 ruff；前端属于锦上添花，不影响运行"],
        ],
        widths=[2.4, 1.0, 3.1],
    )
    caption(doc, "表 8 已知问题清单")
    para(
        doc,
        "已经修复、带回归测试的问题不用再操心：分块 id 撞车导致检索分数错位、FAQ 吞掉例外条款、"
        "模型级拒答缺少转人工出口、BM25 的平方复杂度热点、中文路径下写索引失败、"
        "反向代理缓存后端地址导致前端静默回退假数据、本地启动缺少离线模式导致首次请求卡顿。"
        "完整的排查过程记录在 docs/FAILURE-CASES.md。",
    )

    # 10
    doc.add_heading("10 接手后的工作清单", level=1)
    para(doc, "按投入产出比排序。前两项需要企业真实资料才能推进，其余可以独立开展。")
    table(
        doc,
        ["优先级", "事项", "具体做什么"],
        [
            ["P0", "接入真实资料", "资料放进 backend/data/incoming/，跑 scripts/ingest_folder.py，然后重标阈值并重跑三套评测"],
            ["P0", "重标拒答阈值", "按 docs/INGEST-ENTERPRISE-DATA.md 的五步走一遍，新阈值写回 backend/.env 后重启"],
            ["P1", "对接真实业务系统", "把 order_store.py 的模拟数据换成真实订单与 CRM 接口，保留工具层的超时与降级策略"],
            ["P1", "补齐坐席侧", "转人工后的排队、分配、消息回流；当前只有工单落盘与可选 Webhook"],
            ["P2", "公网部署加固", "鉴权、HTTPS、限额、备份策略与监控接入"],
            ["P2", "扩充评测集", "从真实工单采样，把现有 70 条扩到几百条"],
            ["P3", "前端工程化", "补 ESLint 与 Prettier，补跨浏览器自动化回归"],
        ],
        widths=[0.7, 1.5, 4.3],
    )
    caption(doc, "表 9 建议工作顺序")

    # 11
    doc.add_heading("11 术语表", level=1)
    table(
        doc,
        ["术语", "含义"],
        [
            ["RAG", "检索增强生成：先从知识库检索相关片段，再让模型基于片段作答"],
            ["分块", "把长文档切成适合检索的小段，本项目按段落切分并对超长段落开重叠窗口"],
            ["父子切分", "子块用于检索、父块用于生成，避免答案被切分边界截断"],
            ["BM25", "经典关键词检索算法，本项目与向量检索混合使用"],
            ["命中率 hit@k", "前 k 条检索结果里包含正确目标的次数占比"],
            ["证据命中率", "不仅文档要对，命中的那一段里还要真的包含答案依据"],
            ["拒答阈值", "最高相似度低于该值时判为资料不足并转人工，本项目用原始余弦相似度"],
            ["rerank", "对初步召回的片段做二次精排，本项目实测在当前语料上是负收益，已默认关闭"],
            ["工单", "资料不足或用户要求转人工时生成的记录，带唯一单号"],
            ["审批单", "高风险写操作（如退款）在执行前生成的待批准记录，带幂等键"],
            ["执行轨迹", "一次请求的完整步骤记录，包含意图、工具、耗时、token 与成本，可按 trace_id 查询"],
            ["租户", "多租户隔离标识，通过请求头传递，用于隔离资料、FAQ、会话与工单"],
        ],
        widths=[1.2, 5.3],
    )
    caption(doc, "表 10 术语对照")

    # 12
    doc.add_heading("12 交付与确认记录", level=1)
    para(
        doc,
        "建议在交接会议上逐项确认，并把结果记录在下表中。人事与权限类事项（仓库权限、"
        "密钥轮换、后续维护人）单独确认，避免只交接了代码却没人能改。",
    )
    table(
        doc,
        ["确认项", "结论", "负责人与日期"],
        [
            ["环境能按第 4 节跑起来，五项验证全部通过", "", ""],
            ["密钥位置与轮换方式已确认（第 5 节）", "", ""],
            ["知识库来源与脱敏要求已明确（第 6 节）", "", ""],
            ["已知问题清单已过一遍（第 9 节）", "", ""],
            ["下一步工作优先级已达成一致（第 10 节）", "", ""],
            ["GitHub 仓库权限已移交", "", ""],
            ["后续维护人与响应方式已确定", "", ""],
        ],
        widths=[3.3, 1.4, 1.8],
    )
    caption(doc, "表 11 交接确认记录")

    # 附录
    doc.add_heading("附录 A 关键文件速查", level=1)
    table(
        doc,
        ["想改什么", "看哪个文件"],
        [
            ["接口、请求响应模型", "backend/app/main.py、schemas.py"],
            ["切分规则与块大小", "backend/app/chunking.py"],
            ["换嵌入模型", "backend/app/embeddings.py"],
            ["换向量库", "backend/app/vector_store.py（实现 VectorStore 接口即可）"],
            ["检索融合、阈值、版本过滤", "backend/app/retrieval.py"],
            ["引用格式与父子上下文", "backend/app/pipeline.py"],
            ["资料解析（PDF/Word/Excel/CSV）", "backend/app/ingestion.py"],
            ["提示词、模型参数、流式输出", "backend/app/generation.py"],
            ["工具定义、超时与重试", "backend/app/tools.py"],
            ["工作流状态机与路由规则", "backend/app/workflow.py"],
            ["审批单与幂等", "backend/app/approvals.py"],
            ["FAQ 存储与命中规则", "backend/app/faq_store.py"],
            ["日志、指标与脱敏", "backend/app/observability.py、trace_store.py"],
            ["前端页面与组件", "web/src/App.tsx 与 web/src/components/"],
            ["设计令牌（颜色、字号、圆角）", "web/tailwind.config.js、web/src/index.css"],
        ],
        widths=[2.4, 4.1],
    )
    caption(doc, "表 12 关键文件对照")

    doc.add_heading("附录 B 常用命令", level=1)
    table(
        doc,
        ["目的", "命令"],
        [
            ["启动全栈（本地）", "start-all.bat"],
            ["启动全栈（Docker）", r"powershell -ExecutionPolicy Bypass -File scripts\demo.ps1"],
            ["导入资料", r".\.venv\Scripts\python.exe scripts\ingest_folder.py"],
            ["重标拒答阈值", r"cd backend && ..\.venv\Scripts\python.exe -m evaluation.calibrate_threshold"],
            ["真实语料检索评测", r"..\.venv\Scripts\python.exe -m evaluation.corpus_eval"],
            ["Agent 任务评测", r"..\.venv\Scripts\python.exe -m evaluation.agent_eval --tag full --use-real-embedder --offline"],
            ["单次成本报告", r"..\.venv\Scripts\python.exe -m evaluation.cost_report"],
            ["并发压测", r"..\.venv\Scripts\python.exe -m evaluation.load_test --url http://127.0.0.1:8000 --concurrency 1,10,20 --requests 40"],
            ["后端测试与静态检查", r"cd backend && ..\.venv\Scripts\python.exe -m pytest && ..\.venv\Scripts\python.exe -m ruff check ."],
            ["前端测试与构建", r"cd web && npm test && npm run typecheck && npm run build"],
            ["修复 Docker 启动失败", r"powershell -ExecutionPolicy Bypass -File scripts\fix-docker-socket.ps1"],
            ["推送代码到 GitHub", "git push（凭据已存在 Windows 凭据管理器）"],
        ],
        widths=[1.7, 4.8],
    )
    caption(doc, "表 13 常用命令")

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))
    print("已生成:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成交接文档的 Word 版本")
    parser.add_argument(
        "--template",
        default=None,
        help="可选的版式基底 docx（保留其页面设置与样式表）",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="输出路径")
    args = parser.parse_args()
    build(Path(args.template) if args.template else None, Path(args.out))
