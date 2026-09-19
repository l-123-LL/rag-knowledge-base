"""通过 api.github.com 把当前工作区上传成一个 GitHub 仓库。

为什么要有这个脚本：这台机器到 github.com:443 完全不通（HTTPS/SSH/codeload 都
被拒），`git push` 用不了；但 api.github.com 是通的。所以走 GitHub 的 Git Data API：
blobs → tree → commit → ref，一次提交把工作区传上去，全程不碰 github.com。

代价：这一步只上传**工作区快照**（一个提交），不含本地的 130 多个提交历史。
等网络能连 github.com 时，用 `git remote add origin ... && git push -u origin master`
可以把完整历史补上去（两者不冲突，push 会以本地历史为准）。

用法（仓库根目录）：
    # 方式一：环境变量（推荐用 setx 设置用户级变量后重开终端）
    $env:GITHUB_TOKEN = "..."      # 不要写进任何文件、不要贴到聊天里
    python scripts/publish-to-github.py --repo rag-knowledge-base --private

    # 方式二：令牌文件（脚本只读、不打印；用完记得删）
    #   把令牌写到仓库根目录的 .github-token（已在 .gitignore 里），然后
    python scripts/publish-to-github.py --repo rag-knowledge-base

需要的令牌权限：
  - 细粒度令牌：Repository permissions → Contents: Read and write + Administration: Read and write
  - 或经典令牌：勾选 repo 作用域
"""

import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

API = "https://api.github.com"
TOKEN_FILE = ".github-token"


def read_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        return token
    path = Path(TOKEN_FILE)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise SystemExit(
        f"没有找到令牌：请设置环境变量 GITHUB_TOKEN，或把令牌写入 {TOKEN_FILE}"
    )


def tracked_files() -> list[str]:
    """用 git ls-files 取要上传的文件，天然排除 .gitignore 里的内容。"""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="上传当前工作区到 GitHub")
    parser.add_argument("--repo", required=True, help="仓库名，例如 rag-knowledge-base")
    parser.add_argument("--description", default="企业智能客服 RAG/Agent 问答系统")
    parser.add_argument("--private", action="store_true", help="建私有仓库（默认公开）")
    parser.add_argument("--branch", default="master")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不调接口")
    args = parser.parse_args()

    files = tracked_files()
    print(f"准备上传 {len(files)} 个文件到 {args.repo}（分支 {args.branch}）")

    if args.dry_run:
        for name in files[:10]:
            print(f"  {name}")
        if len(files) > 10:
            print(f"  ... 其余 {len(files) - 10} 个")
        print("dry-run：没有调用任何接口")
        return

    token = read_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "rag-knowledge-base-publisher",
    }

    with httpx.Client(base_url=API, headers=headers, timeout=60.0) as client:
        user = client.get("/user")
        user.raise_for_status()
        owner = user.json()["login"]
        print(f"身份确认：{owner}")

        created = client.post(
            "/user/repos",
            json={
                "name": args.repo,
                "description": args.description,
                "private": args.private,
                "auto_init": False,
            },
        )
        if created.status_code == 422:
            print("仓库已存在，直接往里写")
        else:
            created.raise_for_status()
            print(f"仓库已创建：https://github.com/{owner}/{args.repo}")

        # 1) 逐个上传 blob
        tree: list[dict] = []
        for index, name in enumerate(files, start=1):
            content = Path(name).read_bytes()
            blob = client.post(
                f"/repos/{owner}/{args.repo}/git/blobs",
                json={
                    "content": base64.b64encode(content).decode("ascii"),
                    "encoding": "base64",
                },
            )
            blob.raise_for_status()
            tree.append(
                {
                    "path": name.replace("\\", "/"),
                    "mode": "100755" if os.access(name, os.X_OK) else "100644",
                    "type": "blob",
                    "sha": blob.json()["sha"],
                }
            )
            if index % 25 == 0 or index == len(files):
                print(f"  已上传 {index}/{len(files)}")

        # 2) 建 tree
        tree_response = client.post(
            f"/repos/{owner}/{args.repo}/git/trees",
            json={"tree": tree},
        )
        tree_response.raise_for_status()
        tree_sha = tree_response.json()["sha"]

        # 3) 建 commit（不带 parent，就是首次提交）
        commit = client.post(
            f"/repos/{owner}/{args.repo}/git/commits",
            json={
                "message": "chore: publish working tree from local git repository",
                "tree": tree_sha,
            },
        )
        commit.raise_for_status()
        commit_sha = commit.json()["sha"]

        # 4) 建分支引用
        ref = client.post(
            f"/repos/{owner}/{args.repo}/git/refs",
            json={"ref": f"refs/heads/{args.branch}", "sha": commit_sha},
        )
        if ref.status_code == 422:
            ref = client.patch(
                f"/repos/{owner}/{args.repo}/git/refs/heads/{args.branch}",
                json={"sha": commit_sha, "force": True},
            )
        ref.raise_for_status()

        # 5) 把默认分支也指向它（GitHub 默认 main，这里显式统一）
        client.patch(
            f"/repos/{owner}/{args.repo}",
            json={"default_branch": args.branch},
        )

    print(f"\n完成：https://github.com/{owner}/{args.repo}")
    print("提示：本地已有完整提交历史；网络能连 github.com 时执行")
    print(f"      git remote add origin https://github.com/{owner}/{args.repo}.git")
    print("      git push -u origin master")


if __name__ == "__main__":
    sys.exit(main())
