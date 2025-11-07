"""Set up logging for the documentation build process."""

import atexit
import copy
import importlib
import logging
import logging.handlers
import os
import queue
import threading
import time
import contextvars
from pathlib import Path
from typing import Any, List

from .constants import APP_NAME, BASE_LOG_DIR, GITLOGGER_NAME

# --- Defensive macOS-safe patch ---
logging.raiseExceptions = False  # Suppress internal logging exception tracebacks
_original_emit = logging.StreamHandler.emit


def _safe_emit(self, record):
    try:
        _original_emit(self, record)
    except ValueError:
        # Happens if a background thread logs after sys.stdout/stderr closed.
        pass


logging.StreamHandler.emit = _safe_emit

# --- Default Logging Configuration ---
DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "git_formatter": {
            "format": "[%(asctime)s] [%(levelname)s] [Git] - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "standard",
            "filename": "",
            "level": "DEBUG",
        },
    },
    "loggers": {
        APP_NAME: {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        GITLOGGER_NAME: {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
}

LOGLEVELS = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}

# --- Context-aware global state ---
_LOGGING_STATE: dict[str, contextvars.ContextVar] = {
    "listener": contextvars.ContextVar("listener", default=None),
    "handlers": contextvars.ContextVar("handlers", default=[]),
    "background_threads": contextvars.ContextVar("background_threads", default=[]),
}


def _shutdown_logging():
    """Ensure all logging threads and handlers shut down cleanly."""
    listener = _LOGGING_STATE["listener"].get()
    handlers: List[logging.Handler] = _LOGGING_STATE["handlers"].get()
    bg_threads: List[threading.Thread] = _LOGGING_STATE["background_threads"].get()

    if listener:
        try:
            listener.stop()
        except Exception:
            pass

    for handler in handlers:
        try:
            handler.close()
        except Exception:
            pass

    # Join all registered background threads
    for t in bg_threads:
        if t.is_alive():
            try:
                t.join(timeout=5)
            except Exception:
                pass

    # Reset contextvars
    _LOGGING_STATE["listener"].set(None)
    _LOGGING_STATE["handlers"].set([])
    _LOGGING_STATE["background_threads"].set([])


def register_background_thread(thread: threading.Thread):
    """Register a thread to be joined on logging shutdown."""
    threads = _LOGGING_STATE["background_threads"].get()
    threads.append(thread)
    _LOGGING_STATE["background_threads"].set(threads)


def create_base_log_dir(base_log_dir: str | Path = BASE_LOG_DIR) -> Path:
    """Create the base log directory if it doesn't exist."""
    log_dir = Path(os.getenv("XDG_STATE_HOME", base_log_dir))
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return log_dir


def _resolve_class(path: str):
    """Dynamically imports and returns a class from a string path."""
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def setup_logging(cliverbosity: int, user_config: dict[str, Any] | None = None) -> None:
    """Sets up a non-blocking, configurable logging system."""
    config = copy.deepcopy(DEFAULT_LOGGING_CONFIG)

    if user_config and "logging" in user_config:
        def deep_merge(target: dict, source: dict) -> None:
            for k, v in source.items():
                if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                    deep_merge(target[k], v)
                else:
                    target[k] = v

        deep_merge(config, user_config.get("logging", {}))

    # --- Verbosity & Log File Path Setup ---
    verbosity_level = LOGLEVELS.get(min(cliverbosity, 2), logging.WARNING)
    config["handlers"]["console"]["level"] = logging.getLevelName(verbosity_level)

    log_dir = create_base_log_dir()
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"{APP_NAME}_{timestamp}.log"
    log_path = log_dir / log_filename
    config["handlers"]["file"]["filename"] = str(log_path)

    built_handlers = []

    # --- Handler Initialization ---
    HANDLER_INTERNAL_KEYS = ["class", "formatter", "level", "class_name"]
    FORMATTER_INTERNAL_KEYS = ["class", "formatter", "level", "class_name", "validate"]

    for hname, hconf in config["handlers"].items():
        cls = _resolve_class(hconf["class"])
        handler_args = {k: v for k, v in hconf.items() if k not in HANDLER_INTERNAL_KEYS}
        handler = cls(**handler_args)
        handler.setLevel(hconf.get("level", "NOTSET"))

        formatter_name = hconf.get("formatter")
        if formatter_name and formatter_name in config["formatters"]:
            fmt_conf = config["formatters"][formatter_name]
            formatter_kwargs = {
                k: v for k, v in fmt_conf.items() if k not in FORMATTER_INTERNAL_KEYS and k not in ["format"]
            }
            formatter_kwargs["fmt"] = fmt_conf.get("format")
            formatter_kwargs["datefmt"] = fmt_conf.get("datefmt")
            formatter_kwargs["style"] = fmt_conf.get("style")
            formatter_kwargs = {k: v for k, v in formatter_kwargs.items() if v is not None}
            fmt_cls = _resolve_class(fmt_conf.get("class", "logging.Formatter"))
            handler.setFormatter(fmt_cls(**formatter_kwargs))

        built_handlers.append(handler)

    # --- Asynchronous Queue Setup ---
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    listener = logging.handlers.QueueListener(
        log_queue, *built_handlers, respect_handler_level=True
    )
    listener.start()

    # --- Logger Initialization ---
    for lname, lconf in config["loggers"].items():
        logger = logging.getLogger(lname)
        logger.setLevel(lconf["level"])
        logger.addHandler(queue_handler)
        logger.propagate = lconf.get("propagate", False)

    root_logger = logging.getLogger()
    root_logger.setLevel(config["root"]["level"])
    root_logger.addHandler(queue_handler)

    # --- Register graceful shutdown ---
    _LOGGING_STATE["listener"].set(listener)
    _LOGGING_STATE["handlers"].set(built_handlers)
    atexit.register(_shutdown_logging)
