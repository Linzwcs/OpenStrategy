from dataclasses import dataclass
from typing import Callable, List, Any, Dict
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    PROGRESS_UPDATE = "progress_update"
    METRIC_LOGGED = "metric_logged"
    ARTIFACT_UPLOADED = "artifact_uploaded"
    WORKER_LOG = "worker_log"


@dataclass
class Event:
    type: EventType
    timestamp: datetime
    job_id: str


@dataclass
class JobStarted(Event):

    strategy_name: str

    def __init__(
        self,
        job_id: str,
        strategy_name: str,
    ):
        self.type = EventType.JOB_STARTED
        self.timestamp = datetime.now()
        self.job_id = job_id
        self.strategy_name = strategy_name


@dataclass
class JobCompleted(Event):
    output_path: str
    duration_seconds: float
    total_processed: int

    def __init__(self, job_id: str, output_path: str, duration_seconds: float,
                 total_processed: int):
        self.type = EventType.JOB_COMPLETED
        self.timestamp = datetime.now()
        self.job_id = job_id
        self.output_path = output_path
        self.duration_seconds = duration_seconds
        self.total_processed = total_processed


@dataclass
class JobFailed(Event):
    error_message: str
    traceback: str

    def __init__(self, job_id: str, error_message: str, traceback: str = ""):
        self.type = EventType.JOB_FAILED
        self.timestamp = datetime.now()
        self.job_id = job_id
        self.error_message = error_message
        self.traceback = traceback


@dataclass
class ProgressUpdate(Event):
    completed: int
    total: int
    percent: float
    message: str = ""

    def __init__(self,
                 job_id: str,
                 completed: int,
                 total: int,
                 message: str = ""):
        self.type = EventType.PROGRESS_UPDATE
        self.timestamp = datetime.now()
        self.job_id = job_id
        self.completed = completed
        self.total = total
        self.percent = round((completed / total) * 100, 2) if total > 0 else 0
        self.message = message


@dataclass
class MetricLogged(Event):
    metric_name: str
    metric_value: float

    def __init__(self, job_id: str, metric_name: str, metric_value: float):
        self.type = EventType.METRIC_LOGGED
        self.timestamp = datetime.now()
        self.job_id = job_id
        self.metric_name = metric_name
        self.metric_value = metric_value


@dataclass
class WorkerLog(Event):
    level: str
    message: str

    def __init__(self, job_id: str, level: str, message: str):
        self.type = EventType.WORKER_LOG
        self.timestamp = datetime.now()
        self.job_id = job_id
        self.level = level
        self.message = message


class EventBus:

    _subscribers: Dict[EventType, List[Callable]] = {}
    _global_subscribers: List[Callable] = []

    @classmethod
    def subscribe(cls, callback: Callable, event_type: EventType = None):
        """
        订阅事件
        
        Args:
            callback: 回调函数，接收 Event 对象
            event_type: 事件类型，None 表示订阅所有事件
        """
        if event_type is None:
            cls._global_subscribers.append(callback)
        else:
            if event_type not in cls._subscribers:
                cls._subscribers[event_type] = []
            cls._subscribers[event_type].append(callback)

    @classmethod
    def emit(cls, event: Event):

        for callback in cls._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"[EventBus] Error in global subscriber: {e}")

        if event.type in cls._subscribers:
            for callback in cls._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"[EventBus] Error in {event.type} subscriber: {e}")

    @classmethod
    def clear(cls):

        cls._subscribers.clear()
        cls._global_subscribers.clear()


class ProgressBarListener:

    def __init__(self):
        self.bars = {}

    def __call__(self, event: Event):
        if isinstance(event, JobStarted):
            print(f"✅ Started {event.strategy_name} items)")

        elif isinstance(event, ProgressUpdate):
            print(
                f"\r[{event.completed}/{event.total}] {event.percent}% - {event.message}",
                end="")

        elif isinstance(event, JobCompleted):
            print(f"\n✓ Completed in {event.duration_seconds:.2f}s")

        elif isinstance(event, JobFailed):
            print(f"\n✗ Failed: {event.error_message}")


class MetricsCollector:
    """指标收集器（可对接 Prometheus/W&B）"""

    def __init__(self):
        self.metrics = {}

    def __call__(self, event: Event):
        if isinstance(event, MetricLogged):
            key = f"{event.job_id}:{event.metric_name}"
            self.metrics[key] = event.metric_value

    def export(self) -> Dict[str, float]:
        return self.metrics
