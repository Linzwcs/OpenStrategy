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
from openstrategy.core.introspection import load_strategy_args_from_source
import openstrategy.infra
console = Console()


def print_help_table(title: str, prefix: str, dataclass_type):
    table = Table(title=title, box=None, show_header=True)
    table.add_column(f"Argument ({prefix}.*)", style="green")
    table.add_column("Type", style="magenta")
    table.add_column("Default", style="dim")
    table.add_column("Description", style="white")

    for f in fields(dataclass_type):
        help_text = f.metadata.get("help", "")
        default_val = str(f.default) if f.default != inspect._empty else "?"
        type_name = getattr(f.type, "__name__", str(f.type)).replace("typing.", "")
        table.add_row(f"{prefix}.{f.name}", type_name, default_val, help_text)
    
    console.print(table)
    console.print("")


@click.group()
def cli():
    pass


@cli.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
@click.argument('strategy_id')
@click.option('--help-args', is_flag=True, help="Show available arguments")
@click.pass_context
def run(ctx, strategy_id: str, help_args: bool):
    """
    Run a strategy with strict namespacing.
    
    Usage:
      openstrategy run <id> platform.gpu=1 strategy.lr=0.01
    """
    hub = HubClient()
    
    try:
        strategy_path = hub.download(strategy_id)
    except Exception as e:
        console.print(f"[bold red]Download Failed:[/bold red] {e}")
        sys.exit(1)

    manifest_path = os.path.join(strategy_path, "openstrategy.yaml")
   
    entry_module = "main"
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
            entry_module = data.get("entry_module", "main")
            
    entry_module_path = os.path.join(strategy_path,f"src/{entry_module}.py")
    if os.path.exists(entry_module_path):
        UserStrategyArgs = load_strategy_args_from_source(entry_module_path)
    else:
        UserStrategyArgs = StrategyArgs
    
    if help_args:
        console.print(f"[bold]Strategy:[/bold] {strategy_id}")
        console.print(f"[dim]Path: {strategy_path}[/dim]\n")
        print_help_table("Platform Options", "platform", PlatformArgs)
        print_help_table("Strategy Options", "strategy", UserStrategyArgs)
        return

   
    base_conf = OmegaConf.create({
        "platform": OmegaConf.structured(PlatformArgs),
        "strategy": OmegaConf.structured(UserStrategyArgs)
    })

    OmegaConf.set_struct(base_conf, True)
    cli_conf = OmegaConf.from_cli(ctx.args)

    try:
        final_conf = OmegaConf.merge(base_conf, cli_conf)
        

        platform_obj = OmegaConf.to_object(final_conf.platform)
        strategy_obj = OmegaConf.to_object(final_conf.strategy)

    except Exception as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        console.print("[dim]Hint: Arguments must be prefixed with 'platform.' or 'strategy.'[/dim]")
        console.print(f"[dim]      e.g. platform.gpu=1 strategy.lr=0.01[/dim]")
        sys.exit(1)

    console.print(Panel(
        f"[bold]Platform:[/bold] {platform_obj}\n"
        f"[bold]Strategy:[/bold] {strategy_obj}",
        title=f"🚀 Launching {strategy_id}"
    ))

    # 8. 启动引擎
    config = DEFAULT_CONFIG.copy()
    config['infra']['executor']['type'] = platform_obj.executor
    config['infra']['builder']['type'] = platform_obj.backend # 对应 PlatformArgs 中的 backend
    config['infra']['resources']['gpu'] = platform_obj.gpu

    EventBus.subscribe(ProgressBarListener())
    engine = Engine(config)

    try:
        job_id = engine.run_job(
            strategy_id=strategy_id,
            platform_args=platform_obj,
            strategy_args=strategy_obj
        )
        console.print(f"[bold cyan]Job ID: {job_id}[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]Execution Error: {e}[/bold red]")
        sys.exit(1)
        

@cli.command()
@click.argument('path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('-o', '--output', help='Output filename (default: <dirname>.tar.gz)')
def pack(path: str, output: str):
    """
    Package a strategy directory into a .ops file.
    
    Example:
      openstrategy pack ./example.
    """
    
    if not output:
        folder_name = os.path.basename(os.path.abspath(path))
        output = f"{folder_name}.ops"
        
    yaml_path = os.path.join(path, "openstrategy.yaml")
    if not os.path.exists(yaml_path):
        console.print(f"[bold yellow]Warning:[/bold yellow] {yaml_path} not found. Is this a valid strategy directory?")

    console.print(f"[bold green]📦 Packaging {path} -> {output}[/bold green]")

    try:
        with tarfile.open(output, "w:gz") as tar:
            def filter_func(tarinfo):
                name = tarinfo.name
                if "__pycache__" in name or ".git" in name or ".DS_Store" in name:
                    return None
                return tarinfo
            
            tar.add(path, arcname=".", filter=filter_func)
            
        console.print(f"[bold cyan]Successfully created: {output}[/bold cyan]")
    
        with tarfile.open(output, "r:gz") as tar:
            console.print("[dim]Archive structure:[/dim]")
            for name in tar.getnames()[:10]: 
                console.print(f"  [dim]- {name}[/dim]")
            if len(tar.getnames()) > 10:
                console.print("  [dim]...[/dim]")

    except Exception as e:
        console.print(f"[bold red]Packaging failed: {e}[/bold red]")
        sys.exit(1)
        
      
@cli.command()
@click.argument('strategy_name')
def create(strategy_name: str):
    """
    Initialize a new strategy with a minimal template.
    
    Example:
      openstrategy create my-cool-strategy
    """
    base_path = os.path.abspath(strategy_name)
    
    # 1. Check if directory already exists to prevent overwriting
    if os.path.exists(base_path):
        console.print(f"[bold red]Error:[/bold red] Directory '{strategy_name}' already exists.")
        sys.exit(1)

    console.print(f"[bold green]🚀 Initializing new strategy:[/bold green] {strategy_name}")

    # 2. Define the file contents
    runtime_yaml_content = """backend: "uv"
python_version: "3.10"
dependencies:
  - "requests"
"""

    # We insert the folder name as the strategy name in the YAML
    openstrategy_yaml_content = f"""name: "user/{os.path.basename(strategy_name)}"
version: "0.1.0"
description: "A minimal boilerplate for openstrategy strategies."

entry_module: "main" 
entry_point: "run"
"""

    main_py_content = """from dataclasses import dataclass
import requests
from openstrategy.core.context import Context
from openstrategy.core.args import StrategyArgs

@dataclass
class Params(StrategyArgs):
    message: str = "Hello OpenStrategy!"
    repeat: int = 1

def run(ctx: Context, args: Params):
    print(f"🚀 Task Started: {ctx.task_id}")
    print(f"⚙️  Config: {args}")
    
    for i in range(args.repeat):
        print(f"[{i+1}/{args.repeat}] {args.message}")
"""

    readme_content = f"""# {strategy_name}

This is a strategy created with `openstrategy create`.

## Usage

```bash
openstrategy run [strategy path]
# Or with arguments
openstrategy run [strategy path] strategy.message="Custom Message" strategy.repeat=3
```
"""

    # 3. Define the directory structure and file mapping
    structure = {
        "openstrategy.yaml": openstrategy_yaml_content,
        "runtime.yaml": runtime_yaml_content,
        "Readme.md": readme_content,
        "src/__init__.py": "",
        "src/main.py": main_py_content,
        "assets/.keep": "" # Create assets folder with a hidden keep file
    }

    try:
        # 4. Create files and directories
        for rel_path, content in structure.items():
            full_path = os.path.join(base_path, rel_path)
            dir_name = os.path.dirname(full_path)
            
            # Create directories if they don't exist
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            # Write file content
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        console.print(Panel(
            f"[dim]{base_path}[/dim]\n\n"
            f"├── [bold]src/[/bold]\n"
            f"│   ├── __init__.py\n"
            f"│   └── main.py\n"
            f"├── [bold]assets/[/bold]\n"
            f"├── openstrategy.yaml\n"
            f"├── runtime.yaml\n"
            f"└── Readme.md",
            title="✨ Strategy Created Successfully"
        ))
        
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"  cd {strategy_name}")
        console.print(f"  openstrategy run .")

    except Exception as e:
        console.print(f"[bold red]Failed to create strategy:[/bold red] {e}")
        # Clean up partial creation if necessary, strictly manual for safety here.
        sys.exit(1)
