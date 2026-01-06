import sys
import argparse
import importlib
import logging
import traceback
import json
import os
from pathlib import Path
import inspect
from dataclasses import fields, is_dataclass
from openstrategy.core.context import Context
from openstrategy.core.vfs import JobVFS
from openstrategy.core.args import PlatformArgs, StrategyArgs
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("Launcher")


def hydrate_strategy_args(module, data: dict) -> StrategyArgs:

    TargetClass = StrategyArgs
    
    for name, obj in inspect.getmembers(module):
        if (inspect.isclass(obj) and 
            issubclass(obj, StrategyArgs) and 
            obj is not StrategyArgs):
            TargetClass = obj
            break
        
    valid_keys = {f.name for f in fields(TargetClass)}
    clean_data = {k: v for k, v in data.items() if k in valid_keys}

    return TargetClass(**clean_data)

def load_entry_function(working_dir: str, module_name: str, func_name: str):
    if working_dir not in sys.path:
        sys.path.insert(0, working_dir)

    try:
        logger.info(f"Loading module: {module_name}")
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise RuntimeError(
            f"Failed to import module '{module_name}' in {working_dir}.\nError: {e}"
        )

    if not hasattr(module, func_name):
        raise RuntimeError(
            f"Module '{module_name}' does not have function '{func_name}'")

    func = getattr(module, func_name)

    if not callable(func):
        raise RuntimeError(f"'{module_name}.{func_name}' is not callable.")

    return func

def run():
    parser = argparse.ArgumentParser(description="OpenSynth Generic Launcher")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--func", required=True)
    parser.add_argument("--params", required=True, help="JSON encoded config")

    args = parser.parse_args()

    try:
        os.chdir(args.cwd)
        payload = json.loads(args.params) 
        
        if args.cwd not in sys.path:
            sys.path.insert(0, args.cwd)

        vfs = JobVFS(job_id=args.task_id,
                     workspace_root=Path(payload["vfs_root"]).parent)

        try:
            user_module = importlib.import_module(args.module)
        except ImportError as e:
            raise RuntimeError(f"Failed to import user module '{args.module}': {e}")

     
        args_dict = payload.get("args", {})
        
        platform_data = args_dict.get("platform", {})
        platform_obj = PlatformArgs(**platform_data)
        
        strategy_data = args_dict.get("strategy", payload.get("params", {}))
        strategy_obj = hydrate_strategy_args(user_module, strategy_data)

        ctx = Context(
            task_id=args.task_id,
            working_dir=args.cwd,
            strategy_args=strategy_obj,      
            platform_args=platform_obj,  
            params=payload.get("params", {}),
            vfs=vfs
        )

        if not hasattr(user_module, args.func):
            raise RuntimeError(f"Function '{args.func}' not found in {args.module}")
            
        entry_func = getattr(user_module, args.func)
        
        logger.info(f">>> [Exec] {args.module}.{args.func}(ctx)")
        entry_func(ctx, strategy_obj)
        logger.info("<<< [Done] Execution finished successfully.")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()
