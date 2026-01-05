from typing import Dict, Type, Any, Callable
import importlib
import inspect
from pathlib import Path


class Registry:
    _builders: Dict[str, Type] = {}
    _executors: Dict[str, Type] = {}
    _io_handlers: Dict[str, Type] = {}
    _middlewares: Dict[str, Callable] = {}

    @classmethod
    def register_builder(cls, name: str):

        def decorator(builder_cls):
            cls._builders[name] = builder_cls
            return builder_cls

        return decorator

    @classmethod
    def register_executor(cls, name: str):

        def decorator(executor_cls):
            cls._executors[name] = executor_cls
            return executor_cls

        return decorator

    @classmethod
    def register_io_handler(cls, format: str):

        def decorator(handler_cls):
            cls._io_handlers[format] = handler_cls
            return handler_cls

        return decorator

    @classmethod
    def register_middleware(cls, name: str):

        def decorator(middleware_fn):
            cls._middlewares[name] = middleware_fn
            return middleware_fn

        return decorator

    @classmethod
    def get_builder(cls, name: str) -> Type:
        if name not in cls._builders:
            raise KeyError(
                f"Builder '{name}' not found. Available: {list(cls._builders.keys())}"
            )
        return cls._builders[name]

    @classmethod
    def get_executor(cls, name: str) -> Type:
        if name not in cls._executors:
            raise KeyError(
                f"Executor '{name}' not found. Available: {list(cls._executors.keys())}"
            )
        return cls._executors[name]

    @classmethod
    def get_io_handler(cls, format: str) -> Type:
        if format not in cls._io_handlers:
            raise KeyError(
                f"IO handler '{format}' not found. Available: {list(cls._io_handlers.keys())}"
            )
        return cls._io_handlers[format]

    @classmethod
    def auto_discover_plugins(cls, plugin_dir: str = "plugins"):
        """
        自动发现并加载插件
        类似 Steam Workshop 的自动加载机制
        """
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            return

        for module_path in plugin_path.rglob("*.py"):
            if module_path.name.startswith("_"):
                continue

            # 动态导入模块（会触发装饰器注册）
            module_name = str(module_path.relative_to(
                plugin_path.parent)).replace("/", ".").replace(".py", "")
            try:
                importlib.import_module(module_name)
            except Exception as e:
                print(f"[Registry] Failed to load plugin {module_name}: {e}")

    @classmethod
    def list_available(cls) -> Dict[str, list]:
        """列出所有可用的插件"""
        return {
            "builders": list(cls._builders.keys()),
            "executors": list(cls._executors.keys()),
            "io_handlers": list(cls._io_handlers.keys()),
            "middlewares": list(cls._middlewares.keys())
        }
