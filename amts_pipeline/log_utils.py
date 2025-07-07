"""Daily rotating per-site logger (console + file)."""
from __future__ import annotations
import logging, sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Dict

_LOGGERS: Dict[str, logging.Logger] = {}

def _coerce_level(level) -> int:
    """Accept int or case-insensitive name like 'debug'."""
    if isinstance(level, int):
        return level
    try:
        return logging._nameToLevel[str(level).upper()]
    except KeyError:
        raise ValueError(f"Unknown log level {level!r}") from None

def get_logger(name: str,
               level: int | str = logging.INFO,
               site_root: Path | None = None) -> logging.Logger:
    """
    Return a singleton logger for *name*.

    Parameters
    ----------
    name       : usually `__name__`
    level      : int or "DEBUG"/"INFO"/…
    site_root  : when given, writes daily logs to <site_root>/logs/YYYYMMDD.log
    """
    level_int = _coerce_level(level)

    if name in _LOGGERS:
        log = _LOGGERS[name]
        log.setLevel(level_int)          # allow raising/lowering level later
        return log                       # handlers already attached

    # create fresh logger ----------------------------------------------------
    log = logging.getLogger(name)
    log.setLevel(level_int)
    log.propagate = False   # don’t double-print through the root logger

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    # console ---------------------------------------------------------------
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    # daily rotating file ---------------------------------------------------
    if site_root:
        try:
            log_dir = Path(site_root, "logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            fh = TimedRotatingFileHandler(
                log_dir / "amts.log",
                when="midnight",
                utc=True,
                backupCount=14,          # keep 2 weeks; tune as you like
                encoding="utf-8",
            )
            fh.setFormatter(fmt)
            log.addHandler(fh)
        except Exception as exc:  # pragma: no cover
            # fall back to console only – *don’t* crash the app for logging
            sh.emit(logging.LogRecord(name, logging.WARNING, __file__, 0,
                                      f"Cannot create file handler: {exc}",
                                      None, None))

    _LOGGERS[name] = log
    return log