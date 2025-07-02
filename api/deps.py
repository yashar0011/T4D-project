"""
api.deps
~~~~~~~~
Thin helper layer between FastAPI routes and *amts_pipeline*.

• All heavy work (MAD filter, watcher, plotting, …) lives in *amts_pipeline*.  
• These helpers keep the HTTP layer tiny and **NEVER raise** – on any problem
  they return an **empty DataFrame** so the route can still reply HTTP 200.
"""
from __future__ import annotations

import functools
import glob
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import pandas as pd
from amts_pipeline.settings import load_active_settings

# ───────────────────────── paths ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH      = ROOT / "Settings.xlsx"
FILE_PROFILES_PATH = ROOT / "Settings.xlsx"          # same workbook, 2nd sheet

# ───────────────────────── helpers ────────────────────────────────────────
def _to_bool(x) -> bool:
    """Robust cast for the CSVImport / SQLImport flag columns."""
    if isinstance(x, str):
        return x.strip().lower() in {"true", "1", "yes", "y"}
    return bool(x)

# ───────────────────────── Settings cache ─────────────────────────────────
@functools.lru_cache(maxsize=1)          # reload only when asked
def _settings_cache() -> pd.DataFrame:
    """
    Read **only the first sheet** of *Settings.xlsx*, keep rows where
    ``CSVImport`` is truthy, then return a *clean* DataFrame.

    Columns expected (case-sensitive):

        Site • PointName • Type • CSVImport • SQLImport • SQLSensorID
        TerrestrialPointName • BaselineN/E/H • StartUTC … (+ any extras)

    If a column is missing that’s *okay* – it will end up full of NaNs.
    """
    df = load_active_settings(SETTINGS_PATH)

    if "CSVImport" in df.columns:
        df = df[df["CSVImport"].apply(_to_bool)]

    return df.reset_index(drop=True)


def get_settings(*, refresh: bool = False) -> pd.DataFrame:
    """A **copy** of the cached DataFrame.  Pass ``refresh=True`` to reload."""
    if refresh:
        _settings_cache.cache_clear()
    return _settings_cache().copy()


def list_sites() -> List[str]:
    return sorted(get_settings()["Site"].unique().tolist())


def list_points() -> List[str]:
    return sorted(get_settings()["PointName"].unique().tolist())

# ───────────────────────── File-profile sheet ─────────────────────────────
@functools.lru_cache(maxsize=1)
def get_file_profiles() -> pd.DataFrame:
    """
    Load the **FileProfiles** sheet (second worksheet).

    Expected columns — all optional except *Profile*:

        Profile (str, unique key)
        FileRoot, Pattern, TimeZone,
        ColumnPoint, ColumnTime, ColumnN, ColumnE, ColumnH …

    The sheet is *not* validated here; downstream code decides what it needs.
    """
    try:
        # openpyxl / xlrd is handled by pandas automatically
        return pd.read_excel(FILE_PROFILES_PATH, sheet_name="FileProfiles")
    except Exception:
        # missing sheet → empty DF so the API still works
        return pd.DataFrame()

# ───────────────────────── Δ-CSV helpers ──────────────────────────────────
def _guess_site(point: str) -> str | None:
    df = get_settings()
    rows = df[df["PointName"].str.upper() == point.upper()]
    return rows.iloc[0]["Site"] if not rows.empty else None


def load_deltas(point: str, hours: int = 24) -> pd.DataFrame:
    """
    Concatenate every ``*_dl.csv`` for *point*, clip to *hours* and return a
    UTC-aware, time-sorted DataFrame.  On any problem → **empty DF**.
    """
    try:
        row = get_settings().loc[lambda d: d["PointName"] == point].iloc[0]
    except (KeyError, IndexError):
        return pd.DataFrame()

    if "CSVImport" in row and not _to_bool(row["CSVImport"]):
        return pd.DataFrame()

    export_root = Path(row.get("ExportFolder") or row.get("ImportFolder") or "")
    site = row.get("Site") or _guess_site(point)
    if not export_root or not site:
        return pd.DataFrame()

    pattern = export_root / site / "**" / point / "*_dl.csv"
    frames: list[pd.DataFrame] = []
    for fp in glob.glob(str(pattern), recursive=True):
        try:
            frames.append(pd.read_csv(fp, parse_dates=["TIMESTAMP"]))
        except Exception:
            continue                                      # skip bad files silently

    if not frames:
        return pd.DataFrame()

    big = pd.concat(frames, ignore_index=True)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    if big["TIMESTAMP"].dt.tz is None:
        big["TIMESTAMP"] = big["TIMESTAMP"].dt.tz_localize(timezone.utc)

    return (
        big.loc[big["TIMESTAMP"] >= cutoff]
           .sort_values("TIMESTAMP")
           .reset_index(drop=True)
    )
