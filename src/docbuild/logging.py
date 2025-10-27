"""Set up logging for the documentation build process."""

import atexit
import copy
import importlib
import logging
import logging.handlers
import os
import queue
import time
from pathlib import Path
from typing import Any, Sequence

from .constants import APP_NAME, BASE_LOG_DIR, GITLOGGER_NAME

# --- Default Logging Configuration ---
# This dictionary provides the minimal required configuration structure.
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

LOGLEVELS = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}

def create_base_log_dir(base_log_dir: str | Path = BASE_LOG_DIR) -> Path:
    """Create the base log directory if it doesn't exist.
    
    This directory is typically located at :file:`~/.local/state/docbuild/logs`		
    as per the XDG Base Directory Specification.
    :param base_log_dir: The base directory where logs should be stored.
        Considers the `XDG_STATE_HOME` environment variable if set.
    :return: The path to the base log directory.
    """
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
    user_config: dict[str, Any] | None = None,
) -> None:
    """Sets up a non-blocking, configurable logging system.
    
    This function merges the default logging configuration with the validated
    user configuration and sets up the asynchronous handlers.
    """
    config = copy.deepcopy(DEFAULT_LOGGING_CONFIG)

    if user_config and "logging" in user_config:
        # Use a more robust deep merge approach
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
    
    # --- Handler and Listener Initialization ---
    built_handlers = []
    
    # Required keys to ignore when instantiating a handler (they are for dictConfig lookup)
    HANDLER_INTERNAL_KEYS = ["class", "formatter", "level", "class_name"]
    FORMATTER_INTERNAL_KEYS = ["class", "formatter", "level", "class_name", "validate"] # Added 'validate'

    for hname, hconf in config["handlers"].items():
        cls = _resolve_class(hconf["class"])
        
        handler_args = {
            k: v for k, v in hconf.items() if k not in HANDLER_INTERNAL_KEYS
        }
        
        handler = cls(**handler_args)
        
        handler.setLevel(hconf.get("level", "NOTSET"))
        
        formatter_name = hconf.get("formatter")
        if formatter_name and formatter_name in config["formatters"]:
            fmt_conf = config["formatters"][formatter_name]
            
            # --- FIX APPLIED HERE ---
            # Filter out keys that are Pydantic metadata/aliases (like 'class_name')
            # We specifically filter out 'format' because the Formatter.__init__
            # expects 'fmt' or uses 'style', not 'format' directly as a kwarg.
            formatter_kwargs = {
                k: v for k, v in fmt_conf.items() 
                if k not in FORMATTER_INTERNAL_KEYS and k not in ['format']
            }
            
            # Pass 'fmt' instead of 'format' to the standard Formatter constructor
            formatter_kwargs['fmt'] = fmt_conf.get("format")
            formatter_kwargs['datefmt'] = fmt_conf.get("datefmt")
            formatter_kwargs['style'] = fmt_conf.get("style") # Should pass style if present
            
            # Remove keys that are None
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