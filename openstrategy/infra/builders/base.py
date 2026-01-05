from abc import ABC, abstractmethod
from pathlib import Path
from ...protocol import ExecutionContext, RuntimeConfig


class EnvBuilder(ABC):
    """环境构建器抽象基类"""

    @abstractmethod
    def prepare(self, runtime: RuntimeConfig, strategy_path: Path) -> Path:
        """
        准备环境（下载、编译、安装）。
        返回环境的物理根目录。
        """
        pass

    @abstractmethod
    def get_execution_context(self, env_root: Path) -> ExecutionContext:
        """
        获取用于执行的上下文信息（Python路径、环境变量等）。
        实现 Builder 与 Executor 的解耦。
        """
        pass
