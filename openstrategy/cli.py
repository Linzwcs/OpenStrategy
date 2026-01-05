import click
import sys
from typing import List, Dict, Any
from rich.console import Console
from openstrategy.engine import Engine, DEFAULT_CONFIG
from openstrategy.events import EventBus, ProgressBarListener
from omegaconf import OmegaConf
import openstrategy.infra
import tarfile
import os

console = Console()


@click.group()
def cli():
    pass


@cli.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
@click.argument('strategy_id')
@click.option('--gpu', type=int, default=0, help='[Platform] Number of GPUs')
@click.option('--executor',
              type=click.Choice(['local', 'slurm']),
              default='local',
              help='[Platform] Execution environment')
@click.pass_context
def run(ctx, strategy_id: str, gpu: int, executor: str):
    """
    Run a strategy.
    
    Example:
      opensynth run user/math-logic gpu=1 model.layer=12 lr=0.01
    """

    raw_extra_args = ctx.args

    console.print(f"[bold green]🚀 Launching {strategy_id}[/bold green]")

    try:
        strategy_cli_overrides = OmegaConf.from_cli(raw_extra_args)
        strategy_params_dict = OmegaConf.to_container(strategy_cli_overrides,
                                                      resolve=True)

        console.print(
            f"[dim]Platform Config: GPU={gpu}, Executor={executor}[/dim]")
        if strategy_params_dict:
            console.print(
                f"[dim]Strategy Params:\n{OmegaConf.to_yaml(strategy_cli_overrides)}[/dim]"
            )

    except Exception as e:
        console.print(f"[bold red]Parameter parsing error: {e}[/bold red]")
        sys.exit(1)

    config = DEFAULT_CONFIG.copy()
    config['infra']['executor']['type'] = executor
    config['infra']['resources']['gpu'] = gpu

    EventBus.subscribe(ProgressBarListener())
    engine = Engine(config)

    try:
        job_id = engine.run_job(strategy_id=strategy_id,
                                strategy_args=strategy_params_dict)
        console.print(f"[bold cyan]Job ID: {job_id}[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@cli.command()
@click.argument('path',
                type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('-o',
              '--output',
              help='Output filename (default: <dirname>.tar.gz)')
def pack(path: str, output: str):
    """
    Package a strategy directory into a .tar.gz file without the top-level folder.
    
    Example:
      opensynth pack ./example
    """
    # 确定输出文件名
    if not output:
        folder_name = os.path.basename(os.path.abspath(path))
        output = f"{folder_name}.tar.gz"

    # 校验：确保目录下有 openstrategy.yaml
    yaml_path = os.path.join(path, "openstrategy.yaml")
    if not os.path.exists(yaml_path):
        console.print(
            f"[bold yellow]Warning:[/bold yellow] {yaml_path} not found. Is this a valid strategy directory?"
        )

    console.print(f"[bold green]📦 Packaging {path} -> {output}[/bold green]")

    try:
        with tarfile.open(output, "w:gz") as tar:
            # 过滤函数：忽略 Python 缓存和隐藏文件
            def filter_func(tarinfo):
                name = tarinfo.name
                if "__pycache__" in name or ".git" in name or ".DS_Store" in name:
                    return None
                return tarinfo

            # arcname="." 是关键：它让 path 目录下的内容直接出现在压缩包根目录
            tar.add(path, arcname=".", filter=filter_func)

        console.print(f"[bold cyan]Successfully created: {output}[/bold cyan]")

        # 打印包内结构预览
        with tarfile.open(output, "r:gz") as tar:
            console.print("[dim]Archive structure:[/dim]")
            for name in tar.getnames()[:10]:  # 只展示前10个文件
                console.print(f"  [dim]- {name}[/dim]")
            if len(tar.getnames()) > 10:
                console.print("  [dim]...[/dim]")

    except Exception as e:
        console.print(f"[bold red]Packaging failed: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
