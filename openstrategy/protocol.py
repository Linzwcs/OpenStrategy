from enum import Enum
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Union


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class BackendType(str, Enum):
    UV = "uv"
    DOCKER = "docker"
    REMOTE = "remote"


class Dependency(BaseModel):
    name: str
    version: Optional[str] = None
    source: Optional[str] = None


class RuntimeConfig(BaseModel):
    backend: BackendType = BackendType.UV
    python_version: str = "3.10"
    dependencies: List[Union[str, Dependency]] = []
    env_vars: Dict[str, str] = {}



class StrategyManifest(BaseModel):
    name: str
    version: str = "0.1.0"

    entry_module: str = "main"
    entry_point: str = "run"

    default_config: Dict[str, Any] = {}


class StrategyAsset(BaseModel):
    path: Path
    manifest: StrategyManifest
    runtime: RuntimeConfig


class TaskInput(BaseModel):

    task_id: str
    config: Dict[str, Any]
    data_batch: List[Any]
    output_path: str


class TaskResult(BaseModel):

    task_id: str
    status: TaskStatus
    data: Optional[List[Any]] = None
    error: Optional[str] = None
    metrics: Dict[str, float] = {}


@dataclass
class ExecutionContext:
    """
    环境执行上下文
    Builder 构建完成后返回此对象，Executor 根据此信息配置子进程。
    """
    python_executable: str  # 虚拟环境 Python 绝对路径
    env_vars: Dict[str, str]  # 运行所需环境变量 (PATH, VIRTUAL_ENV)
    working_dir: str  # 建议的工作目录 (通常是策略根目录)
    env_root: str  # 环境物理路径
    python_version: str  # Python 版本
    strategy_package_name: str  # 策略包在环境中的实际注册名 (如 os_strat_xxxx)
