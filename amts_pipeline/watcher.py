# amts_pipeline/watcher.py
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import pandas as pd
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from .cache_utils import Cache
from .cleaner import process_slice
from .log_utils import get_logger
from .settings import load_active_settings

_LOG = get_logger(__name__)

# ───────────────────────── helpers ─────────────────────────────────────────
KEY_COLS: tuple[str, ...] = ("SliceID", )  # single, immutable column
"""Stable, unique key for one slice (used in Cache)."""
def _row_key(r: pd.Series) -> str:
    """Generates a unique key for a row from the settings DataFrame."""
    return str(r["SliceID"])

def _is_row_enabled(val) -> bool:
    """
    Robustly checks if a value is 'truthy'.
    Handles boolean values that might be read from Excel/CSV as strings
    (e.g., "TRUE", "FALSE", "1", "0"). Standard `bool("FALSE")` is `True`,
    which is a bug. This function corrects for that.
    """
    if isinstance(val, str):
        return val.strip().upper() in ("TRUE", "1", "T", "Y", "YES")
    return bool(val)

# ───────────────────────── handler class ───────────────────────────────────
class SettingsHandler(FileSystemEventHandler):
    """Handles file system events for the settings file."""
    def __init__(self, settings_path: Path, force_full: bool = False):
        super().__init__()
        self.path = settings_path.resolve()
        self.force_full = force_full
        self.cache = Cache(self.path)
        # Run the pipeline on initialization
        self.run_pipeline(first_run=True)

    def on_modified(self, event: FileSystemEvent):
        """Callback for when a file is modified in the watched directory."""
        src_path = event.src_path

        # FIX: event.src_path can be str or various byte-like types (bytes,
        # bytearray, memoryview). We must robustly convert it to a string
        # before passing it to Path().
        path_as_str: str
        if isinstance(src_path, str):
            path_as_str = src_path
        elif isinstance(src_path, (bytes, bytearray)):
            # The 'surrogateescape' error handler is robust for file paths.
            path_as_str = src_path.decode('utf-8', 'surrogateescape')
        else:
            # This case handles other potential PathLike but byte-based objects
            # like memoryview by first converting them to bytes.
            path_as_str = bytes(src_path).decode('utf-8', 'surrogateescape')

        # Check if the modified file is the one we are watching.
        if Path(path_as_str).resolve() == self.path:
            _LOG.info("Settings file modification detected.")
            self.run_pipeline()

    def run_pipeline(self, *, first_run: bool = False) -> None:
        """
        Loads settings, determines which slices need processing, and runs them.
        """
        _LOG.info("Running pipeline...")
        df = load_active_settings(self.path)

        if df.empty:
            _LOG.warning("Settings file has no active (CSVImport=TRUE) rows.")
            return

        # The 'force_full' flag, if set at startup, will trigger a full rebuild
        # on the *next modification* of the settings file, not on the initial run.
        if self.force_full and not first_run:
            _LOG.info("'--full' flag is active. Rebuilding all slices.")
            todo = [( _row_key(r), r ) for _, r in df.iterrows()]
            self.cache.data.clear() # Clear cache for a full rebuild
        else:
            # On the initial run, or on changes without the --full flag,
            # we diff against the cache to find what's new or changed.
            # FIX: The `diff` method likely expects the function as a
            # positional argument, not a keyword argument.
            todo = self.cache.diff(df, _row_key)

        if not todo:
            _LOG.info("Settings processed – no relevant changes detected.")
            return

        _LOG.info("Processing %d slice(s)…", len(todo))

        for k, row in todo:
            # CRITICAL FIX: Use the robust boolean check.
            # The simple `bool(row["CSVImport"])` is buggy if the column contains
            # strings like "FALSE", because `bool("FALSE")` evaluates to `True`.
            if not _is_row_enabled(row.get("CSVImport")):
                _LOG.info("Slice '%s' has CSVImport=FALSE – skipped.", row.get("PointName", k))
                continue

            last_ts = self.cache.data.get(k, {}).get("latest_ts")
            last_dt = pd.to_datetime(last_ts) if last_ts else None

            # Process the individual slice
            new_latest = process_slice(row, latest_ts=last_dt)

            if new_latest is not None:
                self.cache.update_latest(k, new_latest)

        self.cache.save()
        _LOG.info("Pipeline run finished.")


# ───────────────────────── public entry-point ──────────────────────────────
def start_watch(settings_path: Path, *, force_full: bool = False) -> None:
    """
    Watches Settings.xlsx for edits and triggers the pipeline.
    • `force_full=True` rebuilds **all** slices on the next change.
    """
    handler = SettingsHandler(settings_path, force_full=force_full)
    observer = Observer()
    # The watchdog `schedule` method expects a string for the path, not a Path object.
    # We convert the Path object to a string using str().
    observer.schedule(handler, str(settings_path.parent), recursive=False)
    observer.start()

    _LOG.info("Watching %s for changes… (Ctrl-C to quit)", settings_path)
    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        _LOG.info("Watcher stopped by user.")
    finally:
        observer.stop()
        observer.join()

