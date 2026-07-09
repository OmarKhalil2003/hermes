import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any

# ContextVars to store correlation identifiers across tasks/coroutines
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as structured JSON."""

    def __init__(self, service_name: str = "backend") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Retrieve context-local tracking IDs
        req_id = request_id_var.get()
        trace_id = trace_id_var.get()

        # Build base structured dictionary
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "logger": record.name,
            "file": f"{record.filename}:{record.lineno}",
            "request_id": req_id,
            "trace_id": trace_id,
        }

        # Inject extra attributes passed during log calls
        # (e.g. extra={"execution_time": 1.25})
        if hasattr(record, "execution_time"):
            log_record["execution_time_ms"] = record.execution_time
        if hasattr(record, "resource_usage"):
            log_record["resource_usage"] = record.resource_usage

        # Format exception details
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logger(
    name: str = "research_assistant", level: str = "INFO"
) -> logging.Logger:
    """Configures and returns a structured JSON logger.

    Args:
        name: Name of the logger instance.
        level: Minimum log level string (DEBUG, INFO, etc.).

    Returns:
        logging.Logger: Configured JSON logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Main application logger
logger = setup_logger(level="INFO")


# Context manager for execution time logging
class LogDuration:
    """Helper to log execution duration of blocks or functions."""

    def __init__(self, action_name: str, log_level: int = logging.INFO) -> None:
        self.action_name = action_name
        self.log_level = log_level
        self.start_time: float = 0.0

    def __enter__(self) -> "LogDuration":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        extra_attrs = {"execution_time": round(duration_ms, 2)}

        if exc_type:
            logger.log(
                logging.ERROR,
                f"Failed action '{self.action_name}': {exc_val}",
                extra=extra_attrs,
                exc_info=(exc_type, exc_val, exc_tb),
            )
        else:
            logger.log(
                self.log_level,
                f"Successfully completed action '{self.action_name}'",
                extra=extra_attrs,
            )
