import click
import sys
import os
import inspect
import importlib.util
from typing import Type
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from omegaconf import OmegaConf
import yaml
from dataclasses import fields, is_dataclass, asdict

from openstrategy.engine import Engine, DEFAULT_CONFIG
from openstrategy.events import EventBus, ProgressBarListener
from openstrategy.hub.client import HubClient
from openstrategy.core.args import PlatformArgs, StrategyArgs
from openstrategy.core.introspection import safe_import_context

console = Console()


def load_strategy_args_schema(strategy_path: str,
                              module_name: str) -> Type[StrategyArgs]:
    """
    在不安装依赖的情况下，提取策略参数定义。
    """
    if strategy_path not in sys.path:
        sys.path.insert(0, strategy_path)

    with safe_import_context():
        try:

            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, StrategyArgs)
                        and obj is not StrategyArgs):
                    return obj

        except Exception as e:
            console.print(
                f"[dim yellow]Could not introspect code: {e}. Using generic args.[/dim yellow]"
            )
        finally:
            if strategy_path in sys.path:
                sys.path.remove(strategy_path)

    return StrategyArgs


def print_help_table(title: str, dataclass_type):
    table = Table(title=title,
                  box=None,
                  show_header=True,
                  header_style="bold cyan")
    table.add_column("Arg", style="green")
    table.add_column("Type", style="magenta")
    table.add_column("Default", style="dim")
    table.add_column("Description", style="white")

    for f in fields(dataclass_type):

        help_text = f.metadata.get("help", "")
        if f.default_factory is not None and f.default_factory != inspect._empty:
            default_val = "<factory>"
        elif f.default != inspect._empty:
            default_val = str(f.default)
        else:
            default_val = "?"

        type_name = getattr(f.type, "__name__",
                            str(f.type)).replace("typing.", "")
        table.add_row(f.name, type_name, default_val, help_text)

    console.print(table)
    console.print("")


@click.group()
def cli():
    pass


@cli.command(context_settings=dict(
    ignore_unknown_options=True,  # 允许未定义的参数（交给 OmegaConf 处理）
    allow_extra_args=True,
))
@click.argument('strategy_id')
@click.option('--help-args', is_flag=True, help="Show all available arguments")
@click.pass_context
def run(ctx, strategy_id: str, help_args: bool):
    """
    Run a strategy.
    
    Example:
      opensynth run user/algo gpu=1 lr=0.01
    """
    hub = HubClient()

    # 1. 必须先下载/定位策略，才能知道有哪些参数
    try:
        strategy_path = hub.download(strategy_id)
    except Exception as e:
        console.print(f"[bold red]Failed to load strategy:[/bold red] {e}")
        sys.exit(1)

    # 2. 读取 manifest 确定入口
    manifest_path = os.path.join(strategy_path, "openstrategy.yaml")
    entry_module = "main"
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
            entry_module = data.get("entry_module", "main")

    StrategyArgsClass = load_strategy_args_schema(strategy_path, entry_module)

    # 4. 如果是帮助模式，直接打印并退出
    if help_args:
        console.print(f"[bold]Strategy Path:[/bold] {strategy_path}")
        print_help_table("Platform Arguments (OpenSynth)", PlatformArgs)
        print_help_table(f"Strategy Arguments ({StrategyArgsClass.__name__})",
                         StrategyArgsClass)
        return

    platform_conf = OmegaConf.structured(PlatformArgs)
    strategy_conf = OmegaConf.structured(StrategyArgsClass)

    cli_conf = OmegaConf.from_cli(ctx.args)

    try:
        platform_merged = OmegaConf.merge(platform_conf, cli_conf)
        platform_obj = OmegaConf.to_object(platform_merged)

        strategy_merged = OmegaConf.merge(strategy_conf, cli_conf)
        strategy_obj = OmegaConf.to_object(strategy_merged)

    except Exception as e:
        console.print(f"[bold red]Parameter Error:[/bold red] {e}")
        console.print("[dim]Use --help-args to see valid parameters.[/dim]")
        sys.exit(1)

    # 6. 展示最终配置
    console.print(
        Panel(
            f"[bold]Platform:[/bold] GPU={platform_obj.gpu}, Exec={platform_obj.executor}\n"
            f"[bold]Strategy:[/bold] {str(strategy_obj)}",
            title=f"🚀 Launching {strategy_id}"))

    # 7. 启动引擎
    config = DEFAULT_CONFIG.copy()
    config['infra']['executor']['type'] = platform_obj.executor
    config['infra']['resources']['gpu'] = platform_obj.gpu

    EventBus.subscribe(ProgressBarListener())
    engine = Engine(config)

    try:
        # 将强类型对象传给 Engine
        job_id = engine.run_job(strategy_id=strategy_id,
                                platform_args=platform_obj,
                                strategy_args=strategy_obj)
        console.print(f"[bold cyan]Job ID: {job_id}[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]Execution Error: {e}[/bold red]")
        sys.exit(1)
