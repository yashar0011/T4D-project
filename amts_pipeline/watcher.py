# amts_pipeline/watcher.py
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import pandas as pd
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .cache_utils import Cache
from .cleaner import process_slice
from .log_utils import get_logger
from .settings import load_active_settings

_LOG = get_logger(__name__)

# ───────────────────────── helpers ─────────────────────────────────────────
KEY_COLS: tuple[str, ...] = ("SliceID", )   # single, immutable column
"""Stable, unique key for one slice (used in Cache)."""
def _row_key(r: pd.Series) -> str:
    return str(r["SliceID"])

# ───────────────────────── handler class ───────────────────────────────────
class SettingsHandler(FileSystemEventHandler):
    def __init__(self, settings_path: Path, force_full: bool = False):
        super().__init__()
        self.path = settings_path.resolve()
        self.force_full = force_full
        self.cache = Cache(self.path)
        self.run_pipeline(first_run=True)

    # watchdog callback ------------
    def on_modified(self, event):
        if Path(event.src_path).resolve() == self.path:  # type: ignore[attr-defined]
            self.run_pipeline()

    # main driver ------------------
    def run_pipeline(self, *, first_run: bool = False) -> None:
        df = load_active_settings(self.path)

        # EARLY-OUT: nothing active
        if df.empty:
            _LOG.warning("Settings.xlsx has no active (CSVImport=TRUE) rows.")
            return

        # compute slices needing work
        if self.force_full and not first_run:
            todo = [( _row_key(r), r ) for _, r in df.iterrows()]
            self.cache.data.clear()
        else:
            todo = self.cache.diff(df, key_fn=_row_key)  # -> List[(key,row)]

        if not todo:
            _LOG.info("Settings saved – no relevant changes detected.")
            return

        _LOG.info("Processing %d slice(s)…", len(todo))

        for k, row in todo:
            # skip disabled rows (CSVImport == FALSE) even if cache said “changed”
            if not bool(row["CSVImport"]):
                _LOG.info("%s CSVImport=FALSE – skipped.", row["PointName"])
                continue

            # latest timestamp already processed
            last_ts = self.cache.data.get(k, {}).get("latest_ts")
            last_dt = pd.to_datetime(last_ts) if last_ts else None

            new_latest = process_slice(row, latest_ts=last_dt)

            if new_latest is not None:
                self.cache.update_latest(k, new_latest)

        self.cache.save()


# ───────────────────────── public entry-point ──────────────────────────────
def start_watch(settings_path: Path, *, force_full: bool = False) -> None:
    """
    Watch *Settings.xlsx* for edits.  
    • Ctrl-C to stop.  
    • `force_full=True` rebuilds **all** slices on the next change.
    """
    handler = SettingsHandler(settings_path, force_full=force_full)
    obs = Observer()
    obs.schedule(handler, settings_path.parent, recursive=False)
    obs.start()

    _LOG.info("Watching %s for changes… (Ctrl-C to quit)", settings_path)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _LOG.info("Watcher stopped by user.")
        obs.stop()

    obs.join()
