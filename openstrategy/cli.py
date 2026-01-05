import click
import sys
from typing import List, Dict, Any
from rich.console import Console
from openstrategy.engine import Engine, DEFAULT_CONFIG
from openstrategy.events import EventBus, ProgressBarListener
from omegaconf import OmegaConf
import openstrategy.infra

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


if __name__ == "__main__":
    cli()
