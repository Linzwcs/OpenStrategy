from dataclasses import dataclass, field
import json
from typing import Dict, Any


@dataclass
class Context:
    """传递给 Worker 的上下文，仅使用标准库"""
    task_id: str
    working_dir: str
    params: Dict[str, Any] = field(default_factory=dict)

    def emit(self, event_type: str, payload: Dict[str, Any]):
        """
        底层发送方法：将事件序列化为 JSON 行，并打印到 Stdout。
        Host 端的 Executor 会捕获并解析这些行。
        """
        message = {
            "__os_event__": True,  # 魔法标记，用于区分普通日志
            "task_id": self.task_id,
            "type": event_type,
            "payload": payload
        }
        # flush=True 确保 Host 能立即收到，而不是卡在缓冲区
        print(json.dumps(message), flush=True)

    def report_progress(self, current: int, total: int, message: str = ""):
        """快捷方法：汇报进度"""
        self.emit(
            "progress", {
                "current": current,
                "total": total,
                "percent": round(current / total * 100, 2),
                "msg": message
            })

    def log_metric(self, name: str, value: float):
        """快捷方法：汇报指标 (如 tokens/s)"""
        self.emit("metric", {"name": name, "value": value})

    def upload_artifact(self, local_path: str, remote_key: str = None):
        """快捷方法：请求 Host 上传文件"""
        self.emit("artifact", {"path": local_path, "key": remote_key})
