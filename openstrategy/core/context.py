from dataclasses import dataclass
from typing import Dict, Any, TypeVar, Generic
from .vfs import JobVFS
from .args import StrategyArgs, PlatformArgs

T = TypeVar("T", bound=StrategyArgs)


@dataclass
class Context(Generic[T]):
    task_id: str
    working_dir: str

    strategy_args: T
    platform_args: PlatformArgs

    params: Dict[str, Any]
    vfs: JobVFS

    @property
    def inputs(self):
        return self.vfs.inputs

    @property
    def outputs(self):
        return self.vfs.outputs

    def checkpoint(self, data: dict):
        self.vfs.save_checkpoint(data)
