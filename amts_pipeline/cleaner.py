"""
Process one Settings slice:  raw CSV  →  MAD filter  →  deltas  →  outputs
---------------------------------------------------------------------------
This function is self-contained; pass it **one row** from Settings.xlsx and it
does everything needed for that point on this run.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import append_datalogger, load_raw_csvs, write_excel
from .log_utils import get_logger
from .mad_utils import mad_filter
from .plotting import make_pdf

logger = get_logger()


def process_slice(row: pd.Series, latest_ts):
    # ------------------------------------------------------------------ meta
    point      = row["PointName"]
    sensor     = row["SQLSensorID"]
    site       = row["Site"]
    start_utc  = pd.to_datetime(row["StartUTC"], utc=True)
    import_dir = Path(row["ImportFolder"]).expanduser()

    # ------------------------------------------------------------------- load
    raw = load_raw_csvs(import_dir)
    if raw.empty:
        logger.warning("%s SID=%s – no raw data", point, sensor)
        return None

    # Parse ISO-like local timestamps → US/Eastern → UTC
    raw["TIMESTAMP"] = (
        pd.to_datetime(
            raw["Event Time (Eastern Standard Time)"],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )
        .dt.tz_localize("US/Eastern", ambiguous="NaT", nonexistent="shift_forward")
        .dt.tz_convert("UTC")
    )

    # ---------------------- NEW:  apply TimeStampOffset (hours) ----------
    try:
        offset_hours = float(row.get("TimeStampOffset", 0) or 0)
        if offset_hours:
            raw["TIMESTAMP"] += pd.to_timedelta(offset_hours, unit="h")
    except Exception:
        logger.warning("%s SID=%s – bad TimeStampOffset value ignored", point, sensor)

    raw = raw.dropna(subset=["TIMESTAMP"])

    # Clip to this slice’s window
    raw = raw[raw["TIMESTAMP"] >= start_utc]
    if latest_ts is not None:
        raw = raw[raw["TIMESTAMP"] > latest_ts]
    if raw.empty:
        return None

    # Accept point-name prefixes (makes “KB-ABC-001” match “KB-ABC-001-FOO”)
    raw = raw[raw["Point Name"].str.upper().str.startswith(point.upper())]
    if raw.empty:
        return None

    # --------------------------------------------------  MAD + deltas ------
    is_reflectless = row["Type"].strip().lower() == "reflectless"
    cols = ["Elevation"] if is_reflectless else ["Northing", "Easting", "Elevation"]

    baselines = {
        "Northing":  row.get("BaselineN", np.nan),
        "Easting":   row.get("BaselineE", np.nan),
        "Elevation": row.get("BaselineH", np.nan),
    }
    mad_thr = row.get("OutlierMAD", 3.5) or 3.5
    clean   = mad_filter(raw, cols, mad_thr, baselines)

    clean["Delta_H_mm"] = (clean["Elevation"] - baselines["Elevation"]) * 1000
    if not is_reflectless:
        clean["Delta_N_mm"] = (clean["Northing"] - baselines["Northing"]) * 1000
        clean["Delta_E_mm"] = (clean["Easting"]  - baselines["Easting"])  * 1000

    # --------------------------------------------------  outputs ----------
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

    # Optional SQL data-logger append
    if bool(row.get("SQLImport", False)):
        append_datalogger(out_dir, point, sensor, clean)

    write_excel(out_dir / f"{point}_{sensor}_{run_date}.xlsx",
                clean, clean.describe().T.reset_index())
    make_pdf(clean, out_dir / f"{point}_{sensor}_{run_date}.pdf")

    logger.info("%s SID=%s → %d new rows", point, sensor, len(clean))
    return clean["TIMESTAMP"].max().to_pydatetime()
