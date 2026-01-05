import subprocess
import os
import threading
import logging
from typing import List, Dict, Optional
import openstrategy
from pathlib import Path
from ...registry import Registry
from ...protocol import ExecutionContext
from .base import Executor

logger = logging.getLogger("LocalExecutor")


@Registry.register_executor("local")
class LocalExecutor(Executor):

    def submit(self,
               cmd: List[str],
               context: ExecutionContext,
               resources: Dict[str, any] = None,
               log_path: Optional[str] = None) -> str:

        resources = resources or {}

        final_env = context.env_vars.copy()
        framework_root = str(Path(openstrategy.__file__).parent.parent)
        final_env["PYTHONPATH"] = framework_root + os.pathsep + final_env.get(
            "PYTHONPATH", "")
        print(final_env)
        if "gpu_indices" in resources:
            gpu_str = ",".join(map(str, resources["gpu_indices"]))
            final_env["CUDA_VISIBLE_DEVICES"] = gpu_str
            logger.info(f"   [LocalExecutor] Assigned GPUs: {gpu_str}")
        else:
            logger.info("   [LocalExecutor] Running on CPU")

        full_cmd = [context.python_executable] + cmd
        logger.info(f"   [LocalExecutor] Spawning: {' '.join(full_cmd)}")

        stdout_dest = subprocess.PIPE
        log_file = None
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            log_file = open(log_path, "a", encoding="utf-8")
            stdout_dest = log_file

        process = None
        try:
            try:
                process = subprocess.Popen(
                    full_cmd,
                    env=final_env,
                    cwd=context.working_dir,
                    stdout=stdout_dest,
                    stderr=subprocess.STDOUT,  # 将错误流合并到标准输出
                    text=True,
                    bufsize=1,
                    shell=False)
            except Exception as spawn_error:
                raise RuntimeError(
                    f"Failed to spawn process (OS error): {spawn_error}")

            if not log_path:
                self._start_log_streamer(process)

            return_code = process.wait()

            if log_file:
                log_file.close()

            # 7. 检查结果
            if return_code != 0:
                error_msg = f"Task failed with exit code: {return_code}"

                # === 关键修改：如果失败了，尝试读取日志文件的最后部分 ===
                if log_path and os.path.exists(log_path):
                    try:
                        with open(log_path,
                                  "r",
                                  encoding="utf-8",
                                  errors='ignore') as f:
                            # 读取最后 2000 个字符
                            f.seek(0, os.SEEK_END)
                            size = f.tell()
                            f.seek(max(0, size - 2000))
                            tail_content = f.read()
                            error_msg += f"\n\n--- [Log Tail Start] ---\n{tail_content}\n--- [Log Tail End] ---"
                    except Exception as read_err:
                        error_msg += f"\n(Could not read log file: {read_err})"

                raise RuntimeError(error_msg)

            logger.info(
                f"   [LocalExecutor] Task {process.pid} finished successfully."
            )

        except Exception as e:
            if log_file and not log_file.closed:
                log_file.close()
            raise e

        return str(process.pid)

    def _start_log_streamer(self, process):

        def stream_logs(proc):
            if proc.stdout:
                try:
                    for line in proc.stdout:
                        print(f"      [Worker-{proc.pid}] {line.strip()}")
                except Exception:
                    pass

        t = threading.Thread(target=stream_logs, args=(process, ))
        t.daemon = True
        t.start()
