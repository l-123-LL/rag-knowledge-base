"""把本仓库发布到 GitHub（默认走 git push，保留完整提交历史）。

背景：这台机器直连 github.com 不通，但本机 127.0.0.1:17890 有可用代理，
经代理访问 github.com / api.github.com 都是 200。所以：
  - 建仓库走 api.github.com；
  - 推代码走 git push（**完整保留本地提交历史**）；
  - 认证用一次性 credential helper 从环境变量读 token，
    不写进 .git/config，也不出现在命令行参数里。

用法（仓库根目录）：
    setx GITHUB_TOKEN "ghp_xxx"          # 或写入仓库根目录的 .github-token（已 gitignore）
    .\\.venv\\Scripts\\python.exe scripts\\publish-to-github.py --repo rag-knowledge-base

常用参数：
    --private           建私有仓库（默认公开）
    --proxy ""          不走代理（网络能直连时）
    --mode api          改用 REST API 只传工作区快照（无提交历史）
    --dry-run           只打印计划

令牌权限：细粒度令牌需要 Contents 读写 + Administration 读写；经典令牌勾 repo。
"""

import argparse
import base64
import os
import subprocess
import sys
from pathlib import Path

import httpx

API = "https://api.github.com"
TOKEN_FILE = ".github-token"
DEFAULT_PROXY = "http://127.0.0.1:17890"


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


def git(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )


def ensure_repo(
    client: httpx.Client, repo: str, private: bool, description: str
) -> None:
    created = client.post(
        "/user/repos",
        json={
            "name": repo,
            "description": description,
            "private": private,
            "auto_init": False,
        },
    )
    if created.status_code == 422:
        print("仓库已存在，直接复用")
        return
    created.raise_for_status()
    print("仓库已创建")


def push_with_git(owner: str, repo: str, branch: str, token: str, proxy: str) -> None:
    """用一次性 credential helper 推送：令牌只经环境变量传给子进程。"""
    url = f"https://github.com/{owner}/{repo}.git"
    proxy_args = (
        ["-c", f"http.proxy={proxy}", "-c", f"https.proxy={proxy}"] if proxy else []
    )
    # helper 从环境变量读令牌；不写入任何配置文件
    helper = '!f() { echo username=x-access-token; echo "password=$GITHUB_TOKEN"; }; f'
    env = {**os.environ, "GITHUB_TOKEN": token}

    git("remote", "remove", "origin")
    git("remote", "add", "origin", url)

    print(f"推送 {branch} → {url}（代理 {proxy or '无'}，保留完整提交历史）")
    result = git(
        *proxy_args,
        "-c",
        f"credential.helper={helper}",
        "push",
        "-u",
        "origin",
        branch,
        env=env,
    )
    if result.stdout.strip():
        print(result.stdout.strip()[-1500:])
    if result.returncode != 0:
        raise SystemExit(f"推送失败（退出码 {result.returncode}）：\n{(result.stderr or '')[-1500:]}")
    print("推送完成，提交历史已保留")


def upload_snapshot(
    client: httpx.Client, owner: str, repo: str, branch: str, files: list[str]
) -> None:
    """备用方案：用 Git Data API 上传工作区快照（只有一个提交）。"""
    tree: list[dict] = []
    for index, name in enumerate(files, start=1):
        blob = client.post(
            f"/repos/{owner}/{repo}/git/blobs",
            json={
                "content": base64.b64encode(Path(name).read_bytes()).decode("ascii"),
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

    tree_sha = client.post(
        f"/repos/{owner}/{repo}/git/trees", json={"tree": tree}
    ).json()["sha"]
    commit = client.post(
        f"/repos/{owner}/{repo}/git/commits",
        json={
            "message": "chore: publish working tree from local git repository",
            "tree": tree_sha,
        },
    )
    commit.raise_for_status()
    ref = client.post(
        f"/repos/{owner}/{repo}/git/refs",
        json={"ref": f"refs/heads/{branch}", "sha": commit.json()["sha"]},
    )
    if ref.status_code == 422:
        client.patch(
            f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
            json={"sha": commit.json()["sha"], "force": True},
        )
    client.patch(f"/repos/{owner}/{repo}", json={"default_branch": branch})
    print("已通过 API 上传工作区快照（不含提交历史）")


def main() -> None:
    parser = argparse.ArgumentParser(description="发布本仓库到 GitHub")
    parser.add_argument("--repo", required=True, help="仓库名，例如 rag-knowledge-base")
    parser.add_argument(
        "--description",
        default="企业智能客服 RAG/Agent 问答系统：混合检索 + 工具工作流 + 评测",
    )
    parser.add_argument("--private", action="store_true", help="建私有仓库（默认公开）")
    parser.add_argument("--branch", default="master")
    parser.add_argument(
        "--proxy", default=DEFAULT_PROXY, help='代理地址，传 "" 表示不走代理'
    )
    parser.add_argument(
        "--mode",
        choices=["git", "api"],
        default="git",
        help="git=推送完整历史；api=只传工作区快照",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = tracked_files()
    print(f"待发布文件：{len(files)} 个（已排除 .gitignore 内容）")
    print(
        f"分支 {args.branch}；模式 {args.mode}；"
        f"可见性 {'私有' if args.private else '公开'}；代理 {args.proxy or '不走代理'}"
    )

    if args.dry_run:
        print("dry-run：没有调用任何接口")
        return

    token = read_token()
    proxy = args.proxy or None
    client_kwargs: dict = {"base_url": API, "timeout": 60.0}
    if proxy:
        client_kwargs["proxy"] = proxy

    with httpx.Client(
        **client_kwargs,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "rag-knowledge-base-publisher",
        },
    ) as client:
        user = client.get("/user")
        if user.status_code == 401:
            raise SystemExit("令牌无效或已过期（401）")
        user.raise_for_status()
        owner = user.json()["login"]
        print(f"身份确认：{owner}")

        ensure_repo(client, args.repo, args.private, args.description)

        if args.mode == "api":
            upload_snapshot(client, owner, args.repo, args.branch, files)
        else:
            push_with_git(owner, args.repo, args.branch, token, proxy)

    print(f"\n完成：https://github.com/{owner}/{args.repo}")


if __name__ == "__main__":
    sys.exit(main())
