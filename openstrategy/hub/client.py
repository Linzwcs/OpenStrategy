import subprocess
from pathlib import Path
from typing import Optional
import os
from .cache import CacheManager


class HubClient:

    def __init__(self):
        self.cache = CacheManager()

    def download(self,
                 strategy_id: str,
                 revision: str = "main",
                 force: bool = False) -> str:
        """
        下载策略并返回本地绝对路径。
        优先检查 strategy_id 是否为本地路径，如果是则直接返回。
        """
        # -------------------------------------------------
        # 1. [新增] 检查本地路径
        # -------------------------------------------------
        # 将输入转换为 Path 对象
        local_target = Path(strategy_id)
        
        # 判断路径是否存在且是一个目录 (假设策略是一个文件夹)
        if local_target.exists() and local_target.is_dir():
            abs_path = local_target.resolve()
            print(f"[*] Found local strategy: {abs_path}")
            
            # 如果是本地路径，通常忽略 revision，但如果用户强制 force 或者指定了非 main 版本
            # 这里可以选择抛出警告，或者仅简单的作为直接使用本地文件处理
            if revision != "main":
                print(f"[*] Warning: 'revision' is ignored for local paths.")
            
            return str(abs_path)

        # -------------------------------------------------
        # 2. 解析 ID -> URL (默认映射到 GitHub)
        # -------------------------------------------------
        # 支持 "username/repo" -> "https://github.com/username/repo.git"
        if "://" in strategy_id:
            repo_url = strategy_id
            # 从 URL 提取 safe name
            safe_name = strategy_id.split("/")[-1].replace(".git", "")
        else:
            repo_url = f"https://github.com/{strategy_id}.git"
            safe_name = strategy_id.replace("/", "_") # 替换斜杠防止路径层级错误

        # -------------------------------------------------
        # 3. 检查缓存
        # -------------------------------------------------
        local_path = self.cache.get_strategy_path(safe_name, revision)

        if self.cache.exists(safe_name, revision) and not force:
            print(f"[*] Found in cache: {local_path}")
            return str(local_path)

        # -------------------------------------------------
        # 4. 执行下载 (Git Clone / Checkout)
        # -------------------------------------------------
        print(f"[*] Downloading {strategy_id} (rev: {revision})...")
        self._git_clone(repo_url, local_path, revision)

        return str(local_path)

    def _git_clone(self, url: str, dest: Path, revision: str):
        """执行 git 操作"""
        if dest.exists():
            import shutil
            shutil.rmtree(dest)

        try:
            # Clone 且只拉取特定深度，减少带宽
            subprocess.run([
                "git", "clone", "--depth", "1", "--branch", revision, url,
                str(dest)
            ],
                           check=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
            
            # 可选：移除 .git 目录
            # import shutil
            # shutil.rmtree(dest / ".git")

        except subprocess.CalledProcessError as e:
            # 简单的错误处理
            # 提示：如果 revision 是 commit hash，'git clone --branch' 会失败
            # 生产环境可能需要先 clone 整个库再 checkout commit
            raise RuntimeError(f"Failed to download strategy: {e.stderr.decode().strip()}")