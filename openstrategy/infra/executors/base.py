from abc import ABC, abstractmethod
from typing import Dict, List, Any


class Executor(ABC):
    """
    算力执行器接口
    负责将任务投递到具体的计算资源
    """

    @abstractmethod
    def submit(self, cmd: List[str], env_vars: Dict[str, str],
               resources: Dict[str, Any], activation_cmd: str) -> str:
        """
        提交任务到执行环境
        
        Args:
            cmd: 要执行的命令 (如 ["python", "runner.py", "task.json"])
            env_vars: 环境变量字典
            resources: 资源需求 (如 {"gpu": 1, "cpu": 4})
            activation_cmd: 环境激活命令
            
        Returns:
            job_id: 任务标识符 (PID 或集群 Job ID)
        """
        pass

    def wait(self, job_id: str) -> int:
        """
        等待任务完成 (可选实现)
        
        Returns:
            exit_code: 任务退出码
        """
        return 0
