"""Set up logging for the documentation build process."""

import atexit
import copy
import importlib
import logging
import logging.handlers
import os
import queue
from pathlib import Path
from typing import Any, Dict, Optional


from .constants import APP_NAME, BASE_LOG_DIR


# --- Default Logging Configuration ---
# This dictionary provides a flexible, default setup that can be easily
# overridden by a user's configuration file.
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
            "level": "INFO",  # Will be set dynamically based on verbosity
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "standard",
            "filename": "",  # Set dynamically in the setup_logging function
            "when": "midnight",
            "backupCount": 4,
            "level": "DEBUG", # All messages are written to the file
        },
    },
    "loggers": {
        APP_NAME: {
            "handlers": ["console", "file"],
            "level": "DEBUG",  # All messages pass through this logger
            "propagate": False,
        },
        f"{APP_NAME}.git": {
            "handlers": ["console", "file"],
            "level": "DEBUG", # All git messages pass through this logger
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG", # CRITICAL: All messages from root and children pass through
    },
}


LOGLEVELS = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}


def create_base_log_dir(base_log_dir: str | Path = BASE_LOG_DIR) -> Path:
    """Creates the base log directory."""
    log_dir = Path(os.getenv("XDG_STATE_HOME", base_log_dir))
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return log_dir


def _resolve_class(path: str):
    """Dynamically imports and returns a class from a string path."""
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def setup_logging(
    cliverbosity: int,
    user_config: Optional[Dict[str, Any]] = None,
) -> None:
    """Sets up a non-blocking, configurable logging system."""
    config = copy.deepcopy(DEFAULT_LOGGING_CONFIG)

    if user_config and "logging" in user_config:
        # Use a more robust deep merge approach
        def deep_merge(target, source):
            for k, v in source.items():
                if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                    deep_merge(target[k], v)
                else:
                    target[k] = v
        
        deep_merge(config, user_config.get("logging", {}))

    # --- Verbosity & Log File Path Setup ---
    # The handler's level determines what gets printed/written.
    verbosity_level = LOGLEVELS.get(min(cliverbosity, 2), logging.WARNING)
    config["handlers"]["console"]["level"] = logging.getLevelName(verbosity_level)

    log_dir = create_base_log_dir()
    log_path = log_dir / f"{APP_NAME}.log"
    config["handlers"]["file"]["filename"] = str(log_path)

    # --- Handler and Listener Initialization ---
    built_handlers = []
    for hname, hconf in config["handlers"].items():
        # Correctly resolve the class from the configuration
        cls = _resolve_class(hconf["class"])
        
        # We must not pass 'level' or 'formatter' to the handler's constructor.
        # They are set using .setLevel() and .setFormatter() methods.
        handler_args = {
            k: v for k, v in hconf.items() if k not in ["class", "formatter", "level"]
        }
        
        handler = cls(**handler_args)

        # Set the level and formatter separately using their methods
        handler.setLevel(hconf.get("level", "NOTSET"))
        fmt_conf = config["formatters"][hconf["formatter"]]
        handler.setFormatter(logging.Formatter(fmt_conf["format"], fmt_conf.get("datefmt")))
        built_handlers.append(handler)
    
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    listener = logging.handlers.QueueListener(
        log_queue, *built_handlers, respect_handler_level=True
    )
    listener.start()
    atexit.register(listener.stop)

    # --- Logger Initialization ---
    for lname, lconf in config["loggers"].items():
        logger = logging.getLogger(lname)
        logger.setLevel(lconf["level"])
        logger.addHandler(queue_handler)
        logger.propagate = lconf.get("propagate", False)
    
    # Configure the root logger separately
    root_logger = logging.getLogger()
    root_logger.setLevel(config["root"]["level"])
    root_logger.addHandler(queue_handler)