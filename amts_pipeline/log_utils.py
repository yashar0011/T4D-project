"""Daily rotating per‑site logger (console + file)."""
import logging
import sys
from pathlib import Path
from datetime import datetime

# A dictionary to hold logger instances so we don't reconfigure them.
_LOGGERS = {}


def get_logger(name: str, level=logging.INFO, site_root: Path | None = None):
    """
    Gets a configured logger instance.

    Args:
        name (str): The name for the logger (e.g., __name__).
        level (int or str): The logging level (e.g., logging.DEBUG or "DEBUG").
        site_root (Path, optional): If provided, logs will also be written to a
                                    file in <site_root>/logs/. Defaults to None.
    """
    # Use the name as the key to allow for multiple distinct loggers
    if name in _LOGGERS:
        return _LOGGERS[name]

    # Create and configure the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Set propagate to False to prevent messages from being sent to the root logger,
    # which avoids duplicate log output.
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # --- Console Handler ---
    # This handler prints logs to the console (standard output).
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # --- File Handler (optional) ---
    # This handler writes logs to a file if a site_root is provided.
    if site_root:
        try:
            log_dir = Path(site_root) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{datetime.utcnow().strftime('%Y%m%d')}.log"
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            logger.error(f"Failed to create file handler for logging: {e}")


    _LOGGERS[name] = logger
    return logger