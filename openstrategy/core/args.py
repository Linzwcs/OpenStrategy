from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlatformArgs:

    gpu: int = field(default=0, metadata={"help": "GPU 数量"})
    cpu: int = field(default=4, metadata={"help": "CPU 核心数"})
    memory: str = field(default="8G", metadata={"help": "内存限制"})
    executor: str = field(default="local",
                          metadata={"help": "执行环境 (local, slurm, k8s)"})

    backend: str = field(default="uv",
                         metadata={"help": "环境构建后端 (uv, docker, conda)"})


@dataclass
class StrategyArgs:
    pass
