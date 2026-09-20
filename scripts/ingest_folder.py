"""批量导入一个文件夹里的企业资料（.md/.txt/.html/.csv/.xlsx/.docx/.pdf）。

为什么用 Python 而不是 PowerShell：multipart 上传在 Windows PowerShell 5.1 里没有
`Invoke-RestMethod -Form`（那是 PowerShell 6+ 的功能），手写 multipart 又容易出错。
httpx 在项目虚拟环境里本来就有，跨版本稳定。

用法（仓库根目录）：
    .\\.venv\\Scripts\\python.exe scripts\\ingest_folder.py
    .\\.venv\\Scripts\\python.exe scripts\\ingest_folder.py --folder "D:\\我的资料" --dry-run

行为：
  - 逐文件上传到 /ingest/file，单个文件失败不影响其它文件；
  - 分块 id 由「来源 + 序号 + 内容哈希」生成，重复导入会被幂等跳过；
  - 结束打印下一步（换语料后必须重新标定拒答阈值）。
"""

import argparse
import os
import sys
from pathlib import Path

import httpx

SUPPORTED = {".md", ".txt", ".html", ".htm", ".csv", ".xlsx", ".xlsm", ".docx", ".pdf"}


def read_admin_key(env_file: Path) -> str:
    if not env_file.exists():
        raise SystemExit(f"找不到 {env_file}")
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("ADMIN_API_KEY"):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise SystemExit(f"{env_file} 里的 ADMIN_API_KEY 是空的")


def collect_files(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="批量导入企业资料")
    parser.add_argument("--folder", default="backend/data/incoming", help="资料目录")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="后端地址")
    parser.add_argument("--env-file", default="backend/.env", help="从这里读 ADMIN_API_KEY")
    parser.add_argument("--dry-run", action="store_true", help="只列文件，不调用接口")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        raise SystemExit(f"找不到文件夹：{folder}，请先建好并把资料放进去")

    files = collect_files(folder)
    print(f"目录：{folder}")
    if not files:
        print(f"没有可导入的文件（支持：{', '.join(sorted(SUPPORTED))}）")
        return

    print(f"找到 {len(files)} 个待导入文件：")
    for path in files:
        print(f"  {path.name}  ({path.stat().st_size / 1024:.0f} KB)")

    if args.dry_run:
        print("\n--dry-run：只列出文件，没有调用接口")
        return

    key = read_admin_key(Path(args.env_file))
    headers = {"X-API-Key": key}
    total_chunks = 0
    failed: list[str] = []

    with httpx.Client(base_url=args.url, timeout=300.0, headers=headers) as client:
        for path in files:
            try:
                with path.open("rb") as handle:
                    response = client.post(
                        "/ingest/file",
                        files={"file": (path.name, handle)},
                    )
                response.raise_for_status()
                chunks = response.json().get("chunk_count", 0)
                total_chunks += chunks
                print(f"  √ {path.name} → 新增 {chunks} 个分块")
            except Exception as exc:  # noqa: BLE001  单文件失败不该中断整批
                failed.append(path.name)
                print(f"  × {path.name} → 导入失败：{exc}")

    print(
        f"\n导入完成：成功 {len(files) - len(failed)} 个，失败 {len(failed)} 个，"
        f"共新增 {total_chunks} 个分块"
    )
    if failed:
        print("失败文件：" + "、".join(failed))
        print("常见原因：PDF 是扫描版（无文字层）、文件加密、或格式不受支持。")

    print(
        "\n下一步（换语料后必须做，否则新资料会因为阈值答不出来）：\n"
        "  1) 把 backend/evaluation/corpus_questions.json 换成你的业务问题（域内 10 条 + 域外 8 条）\n"
        "  2) cd backend && ..\\.venv\\Scripts\\python.exe -m evaluation.calibrate_threshold\n"
        "  3) 把得到的阈值写进 backend/.env 的 RAG_MIN_SCORE，重启后端\n"
        "  4) cd backend && ..\\.venv\\Scripts\\python.exe -m evaluation.corpus_eval"
    )


if __name__ == "__main__":
    sys.exit(main())
