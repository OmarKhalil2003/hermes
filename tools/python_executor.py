import contextlib
import os
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

import psutil
from langchain_core.tools import tool


@tool
def execute_python_code(
    code: str, timeout: int = 5, memory_limit_mb: float = 50.0
) -> str:
    """Execute Python code in an isolated subprocess with resource constraints.

    Args:
        code: The Python code string to execute.
        timeout: Timeout limit in seconds (default is 5).
        memory_limit_mb: Memory cap limit in MB (default is 50.0).

    Returns:
        A string containing stdout/stderr output, or an error description.
    """
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(
        temp_dir, f"sandbox_{uuid_filename()}_{int(time.time())}.py"
    )

    with open(temp_file_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        proc = subprocess.Popen(
            [sys.executable, temp_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.DEVNULL,
        )

        memory_exceeded = False

        def monitor() -> None:
            nonlocal memory_exceeded
            try:
                p = psutil.Process(proc.pid)
                limit_bytes = memory_limit_mb * 1024 * 1024
                while proc.poll() is None:
                    try:
                        total_memory = p.memory_info().rss
                        for child in p.children(recursive=True):
                            total_memory += child.memory_info().rss
                        if total_memory > limit_bytes:
                            memory_exceeded = True
                            proc.kill()
                            return
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    time.sleep(0.01)
            except Exception:
                pass

        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            with contextlib.suppress(Exception):
                stdout, stderr = proc.communicate(timeout=1)
            return f"Error: Execution timed out after {timeout} seconds."

        if memory_exceeded:
            return f"Error: Memory limit of {memory_limit_mb}MB exceeded."

        output = stdout
        if stderr:
            if output:
                output += "\n"
            output += f"Stderr:\n{stderr}"
        return output

    except Exception as e:
        return f"Error running script: {e!s}"

    finally:
        if os.path.exists(temp_file_path):
            with contextlib_suppress(OSError):
                os.remove(temp_file_path)


def uuid_filename() -> str:
    import uuid

    return str(uuid.uuid4())


def contextlib_suppress(*exceptions: Any) -> Any:
    import contextlib

    return contextlib.suppress(*exceptions)
