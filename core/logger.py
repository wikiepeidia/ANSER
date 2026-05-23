"""Centralized application logger.

Usage:
    from core.logger import get_logger
    logger = get_logger(__name__)

Features:
- JSON-formatted log lines (custom Formatter, no third-party dependencies)
- RotatingFileHandler writing to logs/app.log (max 5 MB, 3 backups)
- StreamHandler for console output
- Thread-safe: one handler pair shared across all loggers in this process
"""
import json
import logging
import logging.handlers
import os
import traceback

# Directory where log files will be written (project root / logs/)
_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
_LOG_FILE = os.path.join(_LOGS_DIR, 'app.log')

# Maximum individual log file size and number of backup copies
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3


class _JsonFormatter(logging.Formatter):
    """Format each LogRecord as a single-line JSON string.

    Fields emitted:
        time    – ISO-8601 UTC timestamp
        level   – levelname (DEBUG / INFO / WARNING / ERROR / CRITICAL)
        name    – logger name (usually __name__ of the calling module)
        message – the formatted log message
        exc_info – stringified traceback when an exception is attached, else null
    """

    def format(self, record: logging.LogRecord) -> str:
        exc_text = None
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
        elif record.exc_text:
            exc_text = record.exc_text

        payload = {
            'time': self.formatTime(record, datefmt='%Y-%m-%dT%H:%M:%S'),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'exc_info': exc_text,
        }
        return json.dumps(payload, ensure_ascii=False)


def _build_root_handler_pair():
    """Create and return (file_handler, stream_handler) once per process."""
    os.makedirs(_LOGS_DIR, exist_ok=True)

    fmt = _JsonFormatter()

    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding='utf-8',
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.DEBUG)

    return file_handler, stream_handler


# Module-level singletons — built once when this module is first imported
_file_handler, _stream_handler = _build_root_handler_pair()

# Attach to the root logger so every child logger inherits the handlers
_root = logging.getLogger()
if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in _root.handlers):
    _root.addHandler(_file_handler)
if not any(isinstance(h, logging.StreamHandler) and h is not logging.lastResort for h in _root.handlers):
    _root.addHandler(_stream_handler)

# Set root level; individual loggers can override this
_root.setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that writes JSON to logs/app.log and stdout.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    # Prevent duplicate handlers if the module is reloaded (e.g. during tests)
    logger.propagate = True
    return logger
