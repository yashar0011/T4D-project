"""JSON cache of row‑hashes + last processed epoch."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Callable
import pandas as pd

CACHE_NAME = ".amts_cache.json"
# These are the columns that determine if a row's configuration has changed.
KEY_COLS = [
    "Active", "SensorID", "Site", "PointName", "Type", "ImportFolder",
    "ExportFolder", "BaselineN", "BaselineE", "BaselineH", "OutlierMAD", "StartUTC"
]


def _hash_row(row: pd.Series) -> str:
    """Creates a stable hash from the key columns of a settings row."""
    # Join all key columns into a single string, then hash it.
    # Using .get(c, "") ensures it doesn't fail if a column is missing.
    txt = "||".join(str(row.get(c, "")) for c in KEY_COLS)
    return hashlib.sha1(txt.encode('utf-8')).hexdigest()


class Cache:
    """Tiny disk cache so watcher can diff Settings rows."""

    def __init__(self, settings_path: Path):
        self.cache_path = settings_path.with_name(CACHE_NAME)
        self.data: dict = {}
        if self.cache_path.exists():
            try:
                self.data = json.loads(self.cache_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError) as e:
                # If cache is corrupt or unreadable, start with an empty one.
                print(f"Could not load cache file, starting fresh. Error: {e}")
                self.data = {}

    def diff(self, df_settings: pd.DataFrame, key_fn: Callable[[pd.Series], str]) -> list[tuple[str, pd.Series]]:
        """
        Compares a DataFrame against the cache to find new or changed rows.

        Args:
            df_settings: The current DataFrame of settings to check.
            key_fn: A function that takes a row (pd.Series) and returns a unique key (str).

        Returns:
            A list of tuples, where each tuple contains the key and the row
            for each new or changed item.
        """
        current_hashes, changed_rows = {}, []
        for _, row in df_settings.iterrows():
            # Generate the unique key for the row using the provided function.
            k = key_fn(row)
            h = _hash_row(row)

            # Store the new hash, but preserve the last known timestamp.
            current_hashes[k] = {
                "hash": h,
                "latest_ts": self.data.get(k, {}).get("latest_ts")
            }

            # If the row is new or its hash has changed, add it to the "todo" list.
            if self.data.get(k, {}).get("hash") != h:
                changed_rows.append((k, row))

        # The new set of hashes becomes our current cache data.
        self.data = current_hashes
        return changed_rows

    def update_latest(self, k: str, ts: datetime):
        """Updates the 'latest_ts' for a given key in the cache."""
        if k in self.data:
            self.data[k]["latest_ts"] = ts.isoformat()

    def save(self):
        """Saves the current cache data to the JSON file."""
        try:
            self.cache_path.write_text(json.dumps(self.data, indent=2), encoding='utf-8')
        except IOError as e:
            print(f"Error saving cache file: {e}")
            pass