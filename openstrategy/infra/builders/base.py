# infra/builders/base.py
from abc import ABC, abstractmethod
from openstrategy.protocol import StrategyAsset, ExecutionContext


class EnvBuilder(ABC):
    """环境构建器：将策略转换为可执行环境"""

    @abstractmethod
    def prepare(self, asset: StrategyAsset) -> ExecutionContext:
        """
        Returns:
            ExecutionContext: 包含 python 路径、环境变量、工作目录
        """
        pass

    def get_cache_key(self, asset: StrategyAsset) -> str:
        """计算环境缓存 Key（基于依赖 Hash）"""
        import hashlib
        deps_str = str(sorted(asset.runtime.dependencies))
        return hashlib.sha256(deps_str.encode()).hexdigest()[:12]
