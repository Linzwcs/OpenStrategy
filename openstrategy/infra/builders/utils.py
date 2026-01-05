import os
import ast
import fcntl
import time
import hashlib
from pathlib import Path
from typing import List
import hashlib
import re


def generate_safe_package_name(strategy_id: str, revision: str) -> str:
    """
    生成一个绝对安全的 Python 包名
    Example: user/math-cot -> os_strat_user_math_cot_8f3a12
    """
    # 1. 净化名称，只保留字母数字
    clean_name = re.sub(r'[^a-zA-Z0-9]', '_', strategy_id).lower()

    # 2. 生成哈希 (基于 ID 和 版本) 防止冲突
    unique_str = f"{strategy_id}:{revision}"
    hash_suffix = hashlib.md5(unique_str.encode()).hexdigest()[:8]

    # 3. 拼接前缀
    return f"os_strat_{clean_name}_{hash_suffix}"


class FileLock:
    """基于 fcntl 的跨进程互斥锁 (Unix Only)"""

    def __init__(self, path: Path, timeout: int = 300):
        self.path = path
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = open(self.path, "w")
        start_time = time.time()
        while True:
            try:
                # LOCK_EX: 排他锁, LOCK_NB: 非阻塞
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except IOError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(
                        f"Timeout waiting for lock: {self.path}")
                time.sleep(1)

    def __exit__(self, *args):
        if self.fd:
            fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
            self.fd.close()
            self.fd = None


class ImportValidator:
    """
    策略代码静态检查器
    确保策略包内部只使用相对导入，禁止绝对导入自身包名。
    """

    def __init__(self, strategy_path: Path, package_name: str):
        self.root_path = strategy_path
        self.package_name = package_name

    def validate(self):
        """执行检查，违规直接抛出异常"""
        # 兼容 src 布局
        src_path = self.root_path / "src"
        search_path = src_path if src_path.exists() else self.root_path

        errors = []
        for root, _, files in os.walk(search_path):
            for file in files:
                if file.endswith(".py") and "setup.py" not in file:
                    self._check_file(Path(root) / file, errors)

        if errors:
            raise ValueError(
                f"❌ Code Validation Failed for '{self.package_name}':\n"
                f"Absolute imports of the package itself are forbidden to ensure portability.\n"
                f"{chr(10).join(errors)}\n"
                f"👉 Fix: Change 'from {self.package_name}.x import y' to 'from .x import y'"
            )

    def _check_file(self, file_path: Path, errors: List[str]):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            errors.append(f"  Syntax Error: {file_path}")
            return

        for node in ast.walk(tree):
            # check: import my_pkg
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if self._is_self_import(alias.name):
                        errors.append(
                            f"  {file_path.name}:{node.lineno} -> Forbidden: 'import {alias.name}'"
                        )
            # check: from my_pkg import x
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module and self._is_self_import(
                        node.module):
                    errors.append(
                        f"  {file_path.name}:{node.lineno} -> Forbidden: 'from {node.module} ...'"
                    )

    def _is_self_import(self, name: str) -> bool:
        return name.split(".")[0] == self.package_name
