"""Set up logging for the documentation build process."""

import atexit
from contextlib import suppress
import contextvars
import copy
import importlib
import logging
import logging.handlers
import os
from pathlib import Path
import queue
import threading
import time
from typing import Any, Self

from .constants import APP_NAME, BASE_LOG_DIR, GITLOGGER_NAME

# --- Defensive macOS-safe patch ---
logging.raiseExceptions = False  # Suppress internal logging exception tracebacks
_original_emit = logging.StreamHandler.emit


def _safe_emit(self: Self, record: logging.LogRecord) -> None:  # pyright: ignore[reportGeneralTypeIssues]
    # Happens if a background thread logs after sys.stdout/stderr closed.
    with suppress(ValueError):
        _original_emit(self, record)


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
    # Use None as the default to avoid sharing mutable defaults across
    # contexts. Callers should coerce a None to a fresh list before use.
    "handlers": contextvars.ContextVar("handlers", default=None),
    "background_threads": contextvars.ContextVar("background_threads", default=None),
}


def _shutdown_logging() -> None:
    """Ensure all logging threads and handlers shut down cleanly."""
    listener = _LOGGING_STATE["listener"].get()
    handlers: list[logging.Handler] = _LOGGING_STATE["handlers"].get()
    bg_threads: list[threading.Thread] | None = _LOGGING_STATE[
        "background_threads"
    ].get()

    # Defensive: some tests or earlier code may have mutated the stored
    # value accidentally (e.g. to the `list` type). Coerce to an iterable
    # list to avoid TypeErrors during shutdown.
    if not isinstance(bg_threads, list):
        bg_threads = []

    if listener:
        with suppress(Exception):
            listener.stop()

    for handler in handlers:
        with suppress(Exception):
            handler.close()

    # Join all registered background threads
    for t in bg_threads:
        if t.is_alive():
            with suppress(Exception):
                t.join(timeout=5)

    # Reset contextvars
    _LOGGING_STATE["listener"].set(None)
    _LOGGING_STATE["handlers"].set([])
    _LOGGING_STATE["background_threads"].set([])


def register_background_thread(thread: threading.Thread) -> None:
    """Register a thread to be joined on logging shutdown."""
    threads = _LOGGING_STATE["background_threads"].get()
    if not isinstance(threads, list):
        threads = []
    threads.append(thread)
    _LOGGING_STATE["background_threads"].set(threads)


def create_base_log_dir(base_log_dir: str | Path = BASE_LOG_DIR) -> Path:
    """Create the base log directory if it doesn't exist."""
    log_dir = Path(os.getenv("XDG_STATE_HOME", base_log_dir))
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return log_dir


def _resolve_class(path: str) -> type:
    """Dynamically imports and returns a class from a string path."""
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def build_handlers_from_config(config: dict[str, Any]) -> list[logging.Handler]:
    """Build handler instances from a logging config dict without starting listeners.

    This is a small helper useful for unit tests: it constructs handler
    objects and attaches formatters according to the provided `config`
    but does not start any background listener or register global state.
    """
    built_handlers: list[logging.Handler] = []

    handler_keys = ("class", "formatter", "level", "class_name")
    formatter_keys = ("class", "formatter", "level", "class_name", "validate")

    for _, hconf in config.get("handlers", {}).items():
        cls = _resolve_class(hconf["class"])
        handler_args = {k: v for k, v in hconf.items() if k not in handler_keys}
        handler = cls(**handler_args)
        handler.setLevel(hconf.get("level", "NOTSET"))

        formatter_name = hconf.get("formatter")
        if formatter_name and formatter_name in config.get("formatters", {}):
            fmt_conf = config["formatters"][formatter_name]
            formatter_kwargs = {
                k: v
                for k, v in fmt_conf.items()
                if k not in formatter_keys and k not in ["format"]
            }
            formatter_kwargs["fmt"] = fmt_conf.get("format")
            formatter_kwargs["datefmt"] = fmt_conf.get("datefmt")
            formatter_kwargs["style"] = fmt_conf.get("style")
            formatter_kwargs = {
                k: v for k, v in formatter_kwargs.items() if v is not None
            }
            fmt_cls = _resolve_class(fmt_conf.get("class", "logging.Formatter"))
            handler.setFormatter(fmt_cls(**formatter_kwargs))

        built_handlers.append(handler)

    return built_handlers


def setup_logging(cliverbosity: int, user_config: dict[str, Any] | None = None) -> None:
    """Set up a non-blocking, configurable logging system."""
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

    # Build handlers (use helper to keep logic in one place)
    handlers = build_handlers_from_config(config)

    # --- Asynchronous Queue Setup ---
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    listener = logging.handlers.QueueListener(
        log_queue, *handlers, respect_handler_level=True
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
    _LOGGING_STATE["handlers"].set(handlers)
    atexit.register(_shutdown_logging)
