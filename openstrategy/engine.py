import uuid
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional
import time
import logging

from openstrategy.registry import Registry
from openstrategy.workspace import Workspace
from openstrategy.hub.client import HubClient
from openstrategy.protocol import RuntimeConfig, StrategyManifest, StrategyAsset
from openstrategy.events import EventBus, JobStarted, JobCompleted, JobFailed
from openstrategy.core.vfs import JobVFS

logger = logging.getLogger("Engine")


class Engine:
    """
    OpenSynth 核心调度引擎
    
    职责：
    1. 编排 Hub/Builder/Executor 三层架构
    2. 管理 Job 生命周期
    3. 事件分发
    """

    def __init__(self, config: dict):
        self.config = config

        # 从 Registry 加载插件
        builder_config = config['infra']['builder']
        executor_config = config['infra']['executor']

        builder_cls = Registry.get_builder(builder_config['type'])
        executor_cls = Registry.get_executor(executor_config['type'])

        self.builder = builder_cls(**builder_config.get('params', {}))
        self.executor = executor_cls(**executor_config.get('params', {}))
        self.hub = HubClient()

    def run_job(self, strategy_id: str, strategy_args: dict) -> str:
        job_id = f"job_{uuid.uuid4().hex[:8]}"

        vfs = JobVFS(job_id, workspace_root=Path("runs"))

        strategy_path = self.hub.download(strategy_id)
        asset = self._load_strategy_asset(strategy_path)

        exec_context = self.builder.prepare(asset)

        if "input_file" in strategy_args:
            staged_path = vfs.stage_input(strategy_args["input_file"])
            strategy_args["input_file"] = str(staged_path)

        context_data = {
            "task_id": job_id,
            "working_dir": exec_context.working_dir,
            "params": strategy_args,
            "vfs_root": str(vfs.root)
        }

        launcher_cmd = [
            "-m", "openstrategy.core.launcher", "--task-id", job_id, "--cwd",
            str(exec_context.working_dir), "--module",
            asset.manifest.entry_module, "--func", asset.manifest.entry_point,
            "--params",
            json.dumps(context_data)
        ]

        log_path = str(vfs.logs / "worker.log")
        task_id = self.executor.submit(cmd=launcher_cmd,
                                       context=exec_context,
                                       resources=self.config['infra'].get(
                                           'resources', {}),
                                       log_path=log_path)

        print(f"📋 Job started: {job_id}")
        print(f"📂 Workspace: {vfs.root}")
        print(f"📄 Logs: {log_path}")

        return job_id

    def _load_strategy_asset(self, strategy_path: str) -> StrategyAsset:
        """
        加载策略资产
        读取 manifest.yaml 和 runtime.yaml
        """
        path = Path(strategy_path)

        # 加载 manifest
        manifest_file = path / "manifest.yaml"
        if not manifest_file.exists():
            raise FileNotFoundError(
                f"manifest.yaml not found in {strategy_path}")

        with open(manifest_file) as f:
            manifest_data = yaml.safe_load(f)
            manifest = StrategyManifest(**manifest_data)

        runtime_file = path / "runtime.yaml"
        if runtime_file.exists():
            with open(runtime_file) as f:
                runtime_data = yaml.safe_load(f)
                runtime = RuntimeConfig(**runtime_data)
        else:
            runtime = RuntimeConfig(backend="uv",
                                    python_version="3.10",
                                    dependencies=[])

        return StrategyAsset(path=path, manifest=manifest, runtime=runtime)

    def _wait_for_completion(self, job_id: str, workspace: Workspace,
                             start_time: float):
        """
        等待任务完成并发送完成事件
        （简化版，实际应该监听 Executor 的状态）
        """

        logger.info(f"[Engine] Waiting for {job_id} to complete...")

        duration = time.time() - start_time

        EventBus.emit(
            JobCompleted(
                job_id=job_id,
                output_path=str(workspace.root / "output.jsonl"),
                duration_seconds=duration,
                total_processed=0  # TODO: 从 status.json 读取
            ))

    def get_job_status(self, job_id: str) -> Dict:
        """查询任务状态"""
        workspace = Workspace(job_id)
        return workspace.load_checkpoint()

    def cancel_job(self, job_id: str):
        """取消任务（需要 Executor 支持）"""
        # TODO: 调用 executor.cancel(task_id)
        raise NotImplementedError("Job cancellation not yet implemented")


# === 配置示例 ===
DEFAULT_CONFIG = {
    "infra": {
        "builder": {
            "type": "uv",
            "params": {}
        },
        "executor": {
            "type": "local",
            "params": {}
        },
        "resources": {
            "gpu": 0,
            "cpu": 4
        }
    }
}
