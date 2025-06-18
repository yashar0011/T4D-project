"""Filesystem watcher that only re‑processes changed/added slices."""
from __future__ import annotations
import argparse, time
from pathlib import Path
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd

from .settings import load_active_settings
from .cache_utils import Cache
from .cleaner import process_slice
from .log_utils import get_logger

logger = get_logger()

class SettingsHandler(FileSystemEventHandler):
    def __init__(self, settings_path: Path, force_full: bool = False):
        super().__init__()
        self.settings_path = settings_path.resolve()
        self.force_full = force_full
        self.cache = Cache(self.settings_path)
        self.run_pipeline(first_run=True)

    def on_modified(self, event):
        if Path(event.src_path).resolve() == self.settings_path: # type: ignore
            self.run_pipeline()

    def run_pipeline(self, first_run=False):
        df = load_active_settings(self.settings_path)
        if self.force_full and not first_run:
            changed = [(self.cache.row_key(r), r) for _, r in df.iterrows()]
            self.cache.data = {}  # wipe cache to force rebuild
        else:
            changed = self.cache.diff(df)
        if not changed:
            logger.info("Settings saved – no relevant changes detected.")
            return
        logger.info(f"{len(changed)} slice(s) to process…")
        for k, row in changed:
            # determine slice window
            t0 = pd.to_datetime(row["StartUTC"], utc=True)
            later = df[(df["SensorID"] == row["SensorID"]) &
                        (df["PointName"] == row["PointName"]) &
                        (df["StartUTC"] > row["StartUTC"])]["StartUTC"].min()
            t1 = pd.to_datetime(later, utc=True) if pd.notna(later) else None
            latest_ts = pd.to_datetime(self.cache.data.get(k, {}).get("latest_ts")) if k in self.cache.data else None
            new_latest = process_slice(row, latest_ts)
            if new_latest is not None:
                self.cache.update_latest(k, new_latest)
        self.cache.save()


def start_watch(settings_path: Path, force_full: bool = False):
    handler = SettingsHandler(settings_path, force_full)
    obs = Observer()
    obs.schedule(handler, settings_path.parent, recursive=False)
    obs.start()
    logger.info(f"Watching {settings_path} for changes… (Ctrl‑C to quit)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()