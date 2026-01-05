import os
import subprocess
import hashlib
import shutil
from pathlib import Path
import re
from typing import Optional
from ...protocol import ExecutionContext, StrategyAsset
from ...registry import Registry
from .base import EnvBuilder
import logging

logger = logging.getLogger("UVBuilder")


@Registry.register_builder("uv")
class UVBuilder(EnvBuilder):

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir:
            self.root = Path(cache_dir)
        else:
            self.root = Path.home() / ".cache" / "openstrategy"

        self.venv_root = self.root / "venvs"
        self.shadow_root = self.root / "shadows"

        self.venv_root.mkdir(parents=True, exist_ok=True)
        self.shadow_root.mkdir(parents=True, exist_ok=True)

        if not shutil.which("uv"):
            raise RuntimeError(
                "UV not found. Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"
            )

    def prepare(self, strategy: StrategyAsset) -> ExecutionContext:

        env_dir = self._prepare_venv(strategy)

        safe_pkg_name, shadow_path = self._prepare_shadow_package(strategy)

        python_exe = str(env_dir / "bin" / "python")
        python_path = str(shadow_path.parent)

        logger.info(f"[UVBuilder] Strategy mapped to package: {safe_pkg_name}")

        return ExecutionContext(
            python_executable=python_exe,
            env_vars={
                "VIRTUAL_ENV": str(env_dir),
                "PATH": f"{env_dir / 'bin'}:{os.environ.get('PATH', '')}",
                "PYTHONPATH": python_path,
                "PYTHONUNBUFFERED": "1"
            },
            working_dir=str(shadow_path),
            env_root=str(env_dir),
            python_version=strategy.runtime.python_version,
            strategy_package_name=safe_pkg_name)

    def _prepare_venv(self, strategy: StrategyAsset) -> Path:
        runtime = strategy.runtime
        env_hash = self.get_cache_key(strategy)
        env_dir = self.venv_root / env_hash

        if env_dir.exists() and (env_dir / "pyvenv.cfg").exists():
            return env_dir

        logger.info(f"[UVBuilder] Building shared venv: {env_hash[:8]}...")
        env_dir.mkdir(parents=True, exist_ok=True)

        cmd_venv = [
            "uv", "venv",
            str(env_dir), "--python", runtime.python_version, "--seed"
        ]
        subprocess.run(cmd_venv, check=True, capture_output=True)
        if runtime.dependencies:
            logger.info(
                f"   Installing {len(runtime.dependencies)} dependencies...")

            deps = []
            for d in runtime.dependencies:
                if isinstance(d, str):
                    deps.append(d)
                else:
                    spec = d.name
                    if d.version: spec += f"=={d.version}"
                    deps.append(spec)

            python_exe = env_dir / "bin" / "python"
            subprocess.run(
                ["uv", "pip", "install", "--python",
                 str(python_exe), *deps],
                check=True)
        return env_dir

    def _prepare_shadow_package(self,
                                strategy: StrategyAsset) -> tuple[str, Path]:

        safe_name = self._generate_safe_package_name(strategy.manifest.name,
                                                     str(strategy.path))

        base_dir = self.shadow_root / safe_name
        target_package_dir = base_dir / safe_name

        if base_dir.exists():
            shutil.rmtree(base_dir)

        target_package_dir.mkdir(parents=True)
        src_code_dir = strategy.path / "src"

        logger.info(
            f"[UVBuilder] Copying code from {src_code_dir} -> {target_package_dir}"
        )
        self._copy_tree(src_code_dir, target_package_dir)

        if not (target_package_dir / "__init__.py").exists():
            (target_package_dir / "__init__.py").touch()

        return safe_name, target_package_dir

    def _copy_tree(self, src: Path, dst: Path):
        for item in src.iterdir():
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            if item.name.endswith(".pyc"):
                continue

            s = item
            d = dst / item.name
            if s.is_dir():
                d.mkdir()
                self._copy_tree(s, d)
            else:
                shutil.copy2(s, d)

    def _generate_safe_package_name(self, name: str, unique_key: str) -> str:
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
        hash_suffix = hashlib.md5(unique_key.encode()).hexdigest()[:8]

        return f"os_strat_{clean_name}_{hash_suffix}"
