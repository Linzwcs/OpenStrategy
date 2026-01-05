# core/vfs.py
from pathlib import Path
from typing import Optional


class JobVFS:
    """单个 Job 的文件系统视图"""

    def __init__(self, job_id: str, workspace_root: Path):
        self.job_id = job_id
        self.root = workspace_root / job_id

        # 标准目录结构
        self.inputs = self.root / "inputs"
        self.outputs = self.root / "outputs"
        self.logs = self.root / "logs"
        self.checkpoints = self.root / "checkpoints"

        # 创建目录
        for dir in [self.inputs, self.outputs, self.logs, self.checkpoints]:
            dir.mkdir(parents=True, exist_ok=True)

    def stage_input(self, source: str, name: Optional[str] = None) -> Path:
        """
        将输入文件复制到 inputs/ 目录
        支持本地路径或 URL（未来扩展）
        """
        import shutil
        src = Path(source)
        dst = self.inputs / (name or src.name)

        if src.is_file():
            shutil.copy2(src, dst)
        elif src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            raise FileNotFoundError(f"Input not found: {source}")

        return dst

    def get_output_path(self, filename: str) -> Path:
        """获取输出文件路径"""
        return self.outputs / filename

    def save_checkpoint(self, data: dict, name: str = "state.json"):
        """保存检查点"""
        import json
        path = self.checkpoints / name
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
