"""Daily rotating per‑site logger (console + file)."""
import logging, sys
from pathlib import Path
from datetime import datetime

_LOGGERS = {}


def get_logger(site_root: Path | None = None):
    key = site_root if site_root else "GLOBAL"
    if key in _LOGGERS:
        return _LOGGERS[key]
    logger = logging.getLogger(str(key))
    logger.setLevel(logging.INFO)
    formatted = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")

    # console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatted)
    logger.addHandler(ch)

    # file (if site_root known)
    if site_root:
        log_dir = Path(site_root) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.utcnow().strftime('%Y%m%d')}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatted)
        logger.addHandler(fh)

    _LOGGERS[key] = logger
    return logger