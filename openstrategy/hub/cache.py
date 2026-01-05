import os
import shutil
import hashlib
from pathlib import Path


class CacheManager:

    def __init__(self, cache_dir: str = None):
        # 默认路径: ~/.cache/opensynth/strategies
        if not cache_dir:
            home = Path.home()
            cache_dir = os.environ.get("OPENSYNTH_CACHE",
                                       home / ".cache" / "opensynth")

        self.root = Path(cache_dir) / "strategies"
        self.root.mkdir(parents=True, exist_ok=True)

    def get_strategy_path(self, strategy_id: str, revision: str) -> Path:
        """
        计算策略在本地的存储路径。
        结构: ~/.cache/opensynth/strategies/<user>_<repo>/<commit_hash>
        """
        # 将 slash 替换为下划线作为目录名
        sanitized_id = strategy_id.replace("/", "_")

        # 如果是 latest/main 分支，我们可能需要特殊处理，这里简化为 revision 目录
        repo_dir = self.root / sanitized_id / revision
        return repo_dir

    def exists(self, strategy_id: str, revision: str) -> bool:
        path = self.get_strategy_path(strategy_id, revision)
        # 简单检查：是否存在且包含 manifest.yaml
        return path.exists() and (path / "manifest.yaml").exists()
