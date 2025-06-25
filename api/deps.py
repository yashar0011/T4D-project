"""
Thin helper layer between FastAPI routes and amts_pipeline.

* All heavy lifting (MAD filter, watcher, plots …) lives inside amts_pipeline.
* These helpers keep the HTTP layer tiny and NEVER raise – on any failure they
  simply return an empty DataFrame, so the route can send HTTP 200 + empty JSON.
"""
from __future__ import annotations

import functools, glob
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import pandas as pd

from amts_pipeline.settings import load_active_settings

# --------------------------------------------------------------------------- #
#  Settings helpers
# --------------------------------------------------------------------------- #

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "Settings.xlsx"


@functools.lru_cache(maxsize=1)
def _settings_cache() -> pd.DataFrame:
    """
    Load Settings.xlsx **once** and keep only rows where CSVImport == True.

    We ignore the legacy “Active” column; just delete it from the spreadsheet.
    """
    df = load_active_settings(SETTINGS_PATH)

    # Robust bool casting – supports TRUE/FALSE strings, 1/0, real bools …
    def _to_bool(x):
        if isinstance(x, str):
            return x.strip().lower() in {"true", "1", "yes", "y"}
        return bool(x)

    if "CSVImport" in df.columns:
        df = df[df["CSVImport"].apply(_to_bool)]
    else:  # spreadsheet missing the column – keep everything rather than die
        pass

    return df.reset_index(drop=True)


def get_settings(refresh: bool = False) -> pd.DataFrame:
    """
    Return a COPY of the cached DataFrame.

    Pass `refresh=True` to force reread (handy after you PATCH Settings.xlsx).
    """
    if refresh:
        _settings_cache.cache_clear()
    return _settings_cache().copy()


def list_sites() -> List[str]:
    """Alphabetical list of every *Site* present in the filtered settings."""
    return sorted(get_settings()["Site"].unique().tolist())


def list_points() -> List[str]:
    """Alphabetical list of every *PointName* present in the filtered settings."""
    return sorted(get_settings()["PointName"].unique().tolist())


# --------------------------------------------------------------------------- #
#  Δ-CSV helpers
# --------------------------------------------------------------------------- #


def _guess_site(point: str) -> str | None:
    """Return the first Site that contains *point* (case-insensitive match)."""
    df = get_settings()
    rows = df[df["PointName"].str.upper() == point.upper()]
    return rows.iloc[0]["Site"] if not rows.empty else None


def load_deltas(point: str, hours: int = 24) -> pd.DataFrame:
    """
    Return the last *hours* of Δ-CSV rows for **point**.

    • Clips the time window in UTC.  
    • Sorts by TIMESTAMP.  
    • On any error returns **empty DataFrame** instead of raising.
    """
    try:
        row = get_settings().loc[lambda d: d["PointName"] == point].iloc[0]
    except (KeyError, IndexError):
        return pd.DataFrame()

    # bail out if the user unchecked CSVImport but the UI still asks for it
    if "CSVImport" in row and not bool(row["CSVImport"]):
        return pd.DataFrame()

    export_root = Path(row.get("ExportFolder") or row.get("ImportFolder") or "")
    site = row.get("Site") or _guess_site(point)
    if not export_root or not site:
        return pd.DataFrame()

    pattern = export_root / site / "**" / point / "*_dl.csv"
    csv_paths = glob.glob(str(pattern), recursive=True)
    if not csv_paths:
        return pd.DataFrame()

    dfs: list[pd.DataFrame] = []
    for fp in csv_paths:
        try:
            dfs.append(pd.read_csv(fp, parse_dates=["TIMESTAMP"]))
        except Exception:
            # Skip corrupted/bad CSV but keep going
            continue

    if not dfs:
        return pd.DataFrame()

    big = pd.concat(dfs, ignore_index=True)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    if big["TIMESTAMP"].dt.tz is None:
        big["TIMESTAMP"] = big["TIMESTAMP"].dt.tz_localize(timezone.utc)

    return (
        big.loc[big["TIMESTAMP"] >= cutoff]
        .sort_values("TIMESTAMP")
        .reset_index(drop=True)
    )
