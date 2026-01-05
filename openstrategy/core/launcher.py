import sys
import argparse
import importlib
import logging
import traceback
import json
import os
from pathlib import Path
from openstrategy.core.context import Context
from openstrategy.core.vfs import JobVFS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("Launcher")


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

    parser.add_argument("--module",
                        required=True,
                        help="Entry python module (e.g. main)")
    parser.add_argument("--func",
                        required=True,
                        help="Entry function name (e.g. run)")

    parser.add_argument("--params", required=True, help="JSON encoded config")

    args = parser.parse_args()

    ctx = None

    try:
        os.chdir(args.cwd)
        params = json.loads(args.params)
        vfs = JobVFS(job_id=args.task_id,
                     workspace_root=Path(params["vfs_root"]).parent)

        ctx = Context(task_id=args.task_id,
                      working_dir=args.cwd,
                      params=params.get("params", {}),
                      vfs=vfs)

        entry_func = load_entry_function(args.cwd, args.module, args.func)

        logger.info(f">>> [Exec] {args.module}.{args.func}(ctx)")
        entry_func(ctx)
        logger.info("<<< [Done] Execution finished successfully.")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run()
