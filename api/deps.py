"""Thin wrapper helpers between FastAPI routes and amts_pipeline.

* Heavy lifting (MAD filter, watcher, plots…) lives inside amts_pipeline.
* These helpers keep routes simple and NEVER raise – on any failure they
  return an empty DataFrame; the route converts that to HTTP 200 + empty
  JSON so the front‑end never sees a 5xx.
"""
from __future__ import annotations

import functools, glob
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import pandas as pd

from amts_pipeline.settings import load_active_settings

# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "Settings.xlsx"

@functools.lru_cache(maxsize=1)
def _settings_cache() -> pd.DataFrame:
    """Cache the *active* rows of Settings.xlsx (reload on demand)."""
    return load_active_settings(SETTINGS_PATH).reset_index(drop=True)

def get_settings(refresh: bool = False) -> pd.DataFrame:
    if refresh:
        _settings_cache.cache_clear()
    return _settings_cache().copy()

def list_sites() -> List[str]:
    return sorted(get_settings()["Site"].unique().tolist())

# ---------------------------------------------------------------------------
# Delta helpers
# ---------------------------------------------------------------------------

def _guess_site(point: str) -> str | None:
    df = get_settings()
    rows = df[df["PointName"].str.upper() == point.upper()]
    return rows.iloc[0]["Site"] if not rows.empty else None

def load_deltas(point: str, hours: int = 24) -> pd.DataFrame:
    """Return the last *hours* of Δ‑CSV rows for a point (UTC‑aware)."""
    try:
        row = get_settings().loc[lambda d: d["PointName"] == point].iloc[0]
    except (KeyError, IndexError):
        return pd.DataFrame()

    export_root = Path(row["ExportFolder"] or row["ImportFolder"])
    site = row["Site"] or _guess_site(point)
    if not site:
        return pd.DataFrame()

    pattern = export_root / site / "**" / point / "*_dl.csv"
    csv_paths = glob.glob(str(pattern), recursive=True)
    if not csv_paths:
        return pd.DataFrame()

    dfs: list[pd.DataFrame] = []
    for fp in csv_paths:
        try:
            tmp = pd.read_csv(fp, parse_dates=["TIMESTAMP"])
            dfs.append(tmp)
        except Exception:
            # skip bad CSV
            continue

    if not dfs:
        return pd.DataFrame()

    big = pd.concat(dfs, ignore_index=True)

    # clip to window
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    if big["TIMESTAMP"].dt.tz is None:
        big["TIMESTAMP"] = big["TIMESTAMP"].dt.tz_localize(timezone.utc)

    return (
        big.loc[big["TIMESTAMP"] >= cutoff]
        .sort_values("TIMESTAMP")
        .reset_index(drop=True)
    )