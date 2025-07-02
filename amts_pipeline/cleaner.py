"""
Process one Settings slice:
    raw CSV  →  MAD filter  →  deltas  →  outputs
The function is self-contained; pass it **one row** from Settings.xlsx.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .io_utils    import load_raw_csvs, append_datalogger, write_excel
from .mad_utils   import mad_filter
from .plotting    import make_pdf
from .log_utils   import get_logger

logger = get_logger()


def _to_utc(ts: pd.Series, tz_name: str | None) -> pd.Series:
    """Convert naïve local timestamp strings → UTC (handles DST)."""
    if not tz_name:
        return pd.to_datetime(ts, errors="coerce", utc=True)          # assume already UTC
    return (
        pd.to_datetime(ts, format="%Y-%m-%d %H:%M:%S", errors="coerce")
          .dt.tz_localize(tz_name, ambiguous="NaT", nonexistent="shift_forward")
          .dt.tz_convert("UTC")
    )


def process_slice(row: pd.Series, latest_ts):
    # ───────────────────────── meta ──────────────────────────
    point      = row["PointName"]
    sensor     = row["SQLSensorID"]
    site       = row["Site"]
    tz_name    = row.get("TimeZone")          # NEW column in Settings
    profile_name = row["FileProfile"]
    start_utc  = pd.to_datetime(row["StartUTC"], utc=True)
    import_dir = Path(row["ImportFolder"]).expanduser()

    # ───────────────────────── load ──────────────────────────
    raw = load_raw_csvs(import_dir,profile_name)
    if raw.empty:
        logger.warning("%s SID=%s – no raw data (profile “%s”)", point, sensor, profile_name)
        return None

    raw["TIMESTAMP"] = _to_utc(raw["Event Time (Eastern Standard Time)"], tz_name)
    raw = raw.dropna(subset=["TIMESTAMP"])

    # clip slice window
    raw = raw.loc[raw["TIMESTAMP"] >= start_utc]
    if latest_ts is not None:
        raw = raw.loc[raw["TIMESTAMP"] > latest_ts]
    if raw.empty:
        return None

    # point-name prefix match
    raw = raw[raw["Point Name"].str.upper().str.startswith(point.upper())]
    if raw.empty:
        return None

    # ────────────────── MAD clean + deltas ───────────────────
    is_reflectless = row["Type"].strip().lower() == "reflectless"
    cols = ["Elevation"] if is_reflectless else ["Northing", "Easting", "Elevation"]

    baselines = {
        "Northing":  float(row.get("BaselineN", np.nan)),
        "Easting":   float(row.get("BaselineE", np.nan)),
        "Elevation": float(row.get("BaselineH", np.nan)),
    }
    mad_thr = float(row.get("OutlierMAD", 3.5) or 3.5)
    clean   = mad_filter(raw, cols, mad_thr, baselines)

    clean["Delta_H_mm"] = (clean["Elevation"] - baselines["Elevation"]) * 1000
    if not is_reflectless:
        clean["Delta_N_mm"] = (clean["Northing"] - baselines["Northing"]) * 1000
        clean["Delta_E_mm"] = (clean["Easting"]  - baselines["Easting"])  * 1000

    # ───────────────────── outputs ───────────────────────────
    site_root = Path(row.get("ExportFolder") or row["ImportFolder"])
    run_date  = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir   = site_root / site / run_date / point
    out_dir.mkdir(parents=True, exist_ok=True)

    slice_stamp = start_utc.strftime("%Y%m%dT%H%M%SZ")
    csv_name    = f"{point}_{sensor}_{slice_stamp}.csv"
    clean.to_csv(
        out_dir / csv_name,
        mode="a",
        header=not (out_dir / csv_name).exists(),
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
    )

    # optional SQL append
    if bool(row.get("SQLImport", False)):
        append_datalogger(out_dir, point, sensor, clean)

    write_excel(out_dir / f"{point}_{sensor}_{run_date}.xlsx",
                clean, clean.describe().T.reset_index())
    make_pdf(clean, out_dir / f"{point}_{sensor}_{run_date}.pdf")

    logger.info("%s SID=%s → %d new rows", point, sensor, len(clean))
    return clean["TIMESTAMP"].max().to_pydatetime()
