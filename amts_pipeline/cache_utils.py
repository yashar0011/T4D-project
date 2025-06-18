"""JSON cache of row‑hashes + last processed epoch."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import datetime

CACHE_NAME = ".amts_cache.json"
KEY_COLS = [
    "Active","SensorID","Site","PointName","Type","ImportFolder",
    "ExportFolder","BaselineN","BaselineE","BaselineH","OutlierMAD","StartUTC"
]


def _hash_row(row) -> str:
    txt = "||".join(str(row.get(c, "")) for c in KEY_COLS)
    return hashlib.sha1(txt.encode()).hexdigest()


class Cache:
    """Tiny disk cache so watcher can diff Settings rows."""

    def __init__(self, settings_path: Path):
        self.cache_path = settings_path.with_name(CACHE_NAME)
        self.data = {}
        if self.cache_path.exists():
            try:
                self.data = json.loads(self.cache_path.read_text())
            except Exception:
                self.data = {}

    def row_key(self, row):
        return f"{row['SensorID']}_{row['PointName']}_{row['StartUTC']}"

    def diff(self, df_settings):
        current, changed = {}, []
        for _, row in df_settings.iterrows():
            k = self.row_key(row)
            h = _hash_row(row)
            current[k] = {
                "hash": h,
                "latest_ts": self.data.get(k, {}).get("latest_ts")
            }
            if self.data.get(k, {}).get("hash") != h:
                changed.append((k, row))
        self.data = current
        return changed

    def update_latest(self, k, ts: datetime):
        if k in self.data:
            self.data[k]["latest_ts"] = ts.isoformat()

    def save(self):
        try:
            self.cache_path.write_text(json.dumps(self.data, indent=2))
        except Exception:
            pass