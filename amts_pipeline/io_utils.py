"""
amts_pipeline.io_utils
~~~~~~~~~~~~~~~~~~~~~~
Small helpers used by cleaner / watcher:

* load_raw_csvs  – driven by FileProfiles
* append_datalogger
* write_excel
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import glob
import logging
import zoneinfo
from typing import List

import pandas as pd

from .file_profiles import get_profile, validate_timezone

# ───────────────────────── constants ──────────────────────────────────────
DT_FMT = "%Y-%m-%d %H:%M:%S"
_log   = logging.getLogger(__name__)

# ───────────────────────── loaders ────────────────────────────────────────
def load_raw_csvs(import_dir: Path, profile_name: str) -> pd.DataFrame:
    """
    Read **every CSV matching the FileProfile pattern** inside *import_dir* and
    return **one** DataFrame with unified columns:

        TIMESTAMP (UTC, tz-aware) • POINT_RAW • Northing • Easting • Elevation

    If the profile is missing or no files match → returns *empty* DF.
    Never raises – caller decides what to do.
    """
    prof = get_profile(profile_name)
    if prof is None:
        return pd.DataFrame()

    files: List[str] = glob.glob(str(import_dir / prof["Match"]))
    if not files:
        return pd.DataFrame()

    # column aliases declared in the profile row
    col_time  = prof.get("ColumnTime",       "").strip()
    col_point = prof.get("ColumnPoint",      "").strip()
    col_n     = prof.get("ColumnNorthing",   "").strip()
    col_e     = prof.get("ColumnEasting",    "").strip()
    col_h     = prof.get("ColumnElevation",  "").strip()

    frames: list[pd.DataFrame] = []
    for fp in files:
        try:
            df = pd.read_csv(fp, low_memory=False)

            rename: dict[str, str] = {}
            if col_time  and col_time  in df.columns: rename[col_time]  = "LOCAL_TIME"
            if col_point and col_point in df.columns: rename[col_point] = "POINT_RAW"
            if col_n     and col_n     in df.columns: rename[col_n]     = "Northing"
            if col_e     and col_e     in df.columns: rename[col_e]     = "Easting"
            if col_h     and col_h     in df.columns: rename[col_h]     = "Elevation"

            df = df.rename(columns=rename)

            # ensure the three mandatory columns exist
            if {"LOCAL_TIME", "POINT_RAW", "Elevation"}.issubset(df.columns):
                frames.append(df)
            else:
                _log.warning("File %s skipped – missing mandatory columns", fp)

        except Exception as exc:
            _log.warning("Could not read %s – %s", fp, exc)

    if not frames:
        return pd.DataFrame()

    raw = pd.concat(frames, ignore_index=True)

    # ── time-zone conversion ──────────────────────────────────────────────
    tz_name = validate_timezone(prof.get("TimeZone"))
    tz      = zoneinfo.ZoneInfo(tz_name or "UTC")
    raw["TIMESTAMP"] = (
        pd.to_datetime(raw["LOCAL_TIME"], errors="coerce")
          .dt.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
          .dt.tz_convert("UTC")
    )

    return raw

# ───────────────────────── writers ────────────────────────────────────────
def append_datalogger(out_folder: Path, point: str, sensor: str, df: pd.DataFrame):
    """
    Append ΔH only – two-column CSV suitable for simple SQL bulk-loads.
    Creates the folder hierarchy if needed.
    """
    out_folder.mkdir(parents=True, exist_ok=True)
    out_path = out_folder / f"{point}_{sensor}_dl.csv"
    header   = not out_path.exists()

    df[["TIMESTAMP", "Delta_H_mm"]].to_csv(
        out_path,
        mode="a",
        header=header,
        index=False,
        date_format=DT_FMT,
    )


def write_excel(excel_path: Path,
                combined_df: pd.DataFrame,
                summary_df:  pd.DataFrame):
    """One file, two sheets:  Combined + Summary, frozen headers, no index."""
    import xlsxwriter  # only imported when the function is used

    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as xw:
        combined_df.to_excel(xw, sheet_name="Combined", index=False)
        summary_df.to_excel(xw,  sheet_name="Summary",  index=False)
