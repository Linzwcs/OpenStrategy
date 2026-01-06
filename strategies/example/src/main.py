from openstrategy.core.context import Context
from openstrategy.core.args import StrategyArgs
from dataclasses import dataclass


@dataclass
class MyParams(StrategyArgs):
    lr: float = 1e-4
    optimizer: str = "adamw"


def run(ctx: Context):
    print(f"📌 Task ID: {ctx.task_id}")
    print(f"📂 Inputs dir: {ctx.inputs}")
    print(f"📂 Outputs dir: {ctx.outputs}")

    if list(ctx.inputs.iterdir()):
        print(f"✅ Found inputs: {list(ctx.inputs.iterdir())}")
    print(f"=========strat args==========")
    for k, v in ctx.strategy_args.items():
        print(f"{k}: {v}")
    print(f"=========end args==========")
    print(f"=========strat args==========")
    for k, v in ctx.platform_args.items():
        print(f"{k}: {v}")
    print(f"=========end args==========")
    output_file = ctx.outputs / "result.txt"
    output_file.write_text("Hello from OpenSynth!")
    print(f"✅ Wrote output: {output_file}")

    ctx.checkpoint({"status": "completed", "items_processed": 42})
    print(f"✅ Saved checkpoint")
