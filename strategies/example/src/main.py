import time
import json
import logging
import random
from dataclasses import dataclass, field, asdict
from typing import List, Dict
from pathlib import Path

from openstrategy.core.context import Context
from openstrategy.core.args import StrategyArgs


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("ComplexStrategy")

@dataclass
class TrainParams(StrategyArgs):
    
    model_name: str = "bert-base-uncased"
    lr: float = 5e-5
    batch_size: int = 32
    epochs: int = 3
    
    optimizer: str = "adamw"
    weight_decay: float = 0.01
    
    metrics: List[str] = field(default_factory=lambda: ["accuracy", "f1_score"])
    
    use_fp16: bool = True
    dry_run: bool = False 

def run(ctx: Context, args: TrainParams):
    """
    OpenStrategy 标准入口函数。
    
    Args:
        ctx (Context): 包含任务ID、文件路径、平台资源信息 (Environment)
        args (TrainParams): 用户定义的强类型参数 (Configuration)
    """
    
    print(f"\n{'='*20} 🚀 Strategy Started {'='*20}")
    print(f"📌 Task ID    : {ctx.task_id}")
    print(f"📂 Workspace  : {ctx.working_dir}")
    print(f"🔧 Executor   : {ctx.platform_args.executor}")
    print(f"🏗️  Backend    : {ctx.platform_args.backend}")
    
 
    if ctx.platform_args.gpu > 0:
        print(f"⚡ GPU Mode   : Activated ({ctx.platform_args.gpu} devices)")
        device = "cuda"
    else:
        print(f"🐢 CPU Mode   : Activated (No GPU assigned)")
        device = "cpu"


    print(f"\n--- ⚙️ Configuration ---")
    
    config_dict = asdict(args)
    for k, v in config_dict.items():
        print(f"  • {k:<15}: {v}")
    print("-" * 25 + "\n")

    if args.dry_run:
        logger.warning("Dry run enabled. Skipping execution.")
        return


    data_path = None
    
    
    logger.info(f"Initializing model {args.model_name} on {device}...")
    logger.info(f"Optimizer: {args.optimizer}, LR: {args.lr}")

    history = []
    
    for epoch in range(1, args.epochs + 1):
        
        logger.info(f"🔄 Starting Epoch {epoch}/{args.epochs}")
        time.sleep(1.0) 
        epoch_metrics = {
            "epoch": epoch,
            "loss": round(random.uniform(0.1, 0.9) / epoch, 4),
        }
    
        for m in args.metrics:
            epoch_metrics[m] = round(random.uniform(0.8, 0.99), 4)

        history.append(epoch_metrics)
        print(f"   ✅ Epoch {epoch} Result: {epoch_metrics}")
        
        checkpoint_data = {
            "status": "training",
            "current_epoch": epoch,
            "model_state": "mock_binary_data",
            "args": config_dict
        }
        ctx.checkpoint(checkpoint_data)
        logger.debug(f"Saved checkpoint for epoch {epoch}")

    logger.info("Training completed. Saving artifacts...")

    model_file = ctx.outputs / "model.bin"
    model_file.write_bytes(b"mock_model_weights_0x123456")
    logger.info(f"💾 Model saved to: {model_file}")

    metrics_file = ctx.outputs / "metrics.json"
    result = {
        "final_metrics": history[-1],
        "history": history,
        "device": device,
        "platform_args_info": asdict(ctx.platform_args)
    }
    
    with open(metrics_file, "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"📊 Metrics saved to: {metrics_file}")
    print(f"\n🎉 Task {ctx.task_id} Finished Successfully!")