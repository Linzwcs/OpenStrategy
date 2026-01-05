from dataclasses import dataclass, field
import json
from typing import Dict, Any
from .vfs import JobVFS


@dataclass
class Context:
    task_id: str
    working_dir: str
    params: Dict[str, Any]
    vfs: JobVFS  # 新增

    # 提供友好的 API
    @property
    def inputs(self):
        return self.vfs.inputs

    @property
    def outputs(self):
        return self.vfs.outputs

    def checkpoint(self, data: dict):
        self.vfs.save_checkpoint(data)
