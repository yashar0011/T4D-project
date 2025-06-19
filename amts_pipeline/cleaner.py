"""Process one Settings slice: load raw → MAD filter → delta → outputs."""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from .mad_utils import mad_filter
from .io_utils import load_raw_csvs, append_datalogger, write_excel
from .plotting import make_pdf
from .log_utils import get_logger

logger = get_logger()


def process_slice(row: pd.Series, latest_ts):
    """Given one active Settings row, read raw CSVs, remove outliers,
    calculate deltas, and write CSV / Excel / PDF outputs.

    Parameters
    ----------
    row : pd.Series
        The Settings row for this (SensorID, PointName, StartUTC) slice.
    latest_ts : datetime | None
        The latest TIMESTAMP already processed for this slice, or None on first run.

    Returns
    -------
    datetime | None
        The new latest TIMESTAMP processed, or None if no rows were written.
    """
    # ── unpack settings row ────────────────────────────────────────────
    point   = row["PointName"]
    sensor  = row["SensorID"]
    site    = row["Site"]
    import_dir = Path(row["ImportFolder"]).expanduser()
    start_utc   = pd.to_datetime(row["StartUTC"], utc=True)

    # ── load raw files ────────────────────────────────────────────────
    raw = load_raw_csvs(import_dir)
    if raw.empty:
        logger.warning(f"{point} SID={sensor} – no raw data")
        return None

    # ── robust timestamp → EST → UTC ─────────────────────────────────
    raw["TIMESTAMP"] = (
        pd.to_datetime(
            raw["Event Time (Eastern Standard Time)"],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )
        .dt.tz_localize("US/Eastern", ambiguous="NaT", nonexistent="shift_forward")
        .dt.tz_convert("UTC")
    )
    raw = raw.dropna(subset=["TIMESTAMP"])

    # keep only rows in [StartUTC, ∞) and newer than cache
    raw = raw[raw["TIMESTAMP"] >= start_utc]
    if latest_ts is not None:
        raw = raw[raw["TIMESTAMP"] > latest_ts]

    # ── agile point-name prefix match ─────────────────────────────────
    primary = point.upper()
    raw = raw[raw["Point Name"].str.upper().str.startswith(primary)]
    if raw.empty:
        return None

    # ── outlier removal & delta calculation ──────────────────────────
    cols = (
        ["Elevation"]
        if row["Type"].lower() == "reflectless"
        else ["Northing", "Easting", "Elevation"]
    )
    baselines = {
        "Northing": row["BaselineN"],
        "Easting":  row["BaselineE"],
        "Elevation": row["BaselineH"],
    }
    clean = mad_filter(raw, cols, row["OutlierMAD"], baselines)

    clean.insert(0, "PointName", point)   
    clean.insert(1, "SensorID",  sensor) 
    clean.insert(2, "Site",      site)   

    clean["Delta_H_mm"] = (clean["Elevation"] - float(row["BaselineH"])) * 1000
    if row["Type"].lower() == "reflective":
        clean["Delta_N_mm"] = (clean["Northing"] - float(row["BaselineN"])) * 1000
        clean["Delta_E_mm"] = (clean["Easting"]  - float(row["BaselineE"])) * 1000

    # ── output paths ─────────────────────────────────────────────────
    site_root = Path(row["ExportFolder"] or row["ImportFolder"])
    run_date  = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir   = site_root / site / run_date / point
    out_dir.mkdir(parents=True, exist_ok=True)

    slice_stamp = start_utc.strftime("%Y%m%dT%H%M%SZ")
    csv_name    = f"{point}_{sensor}_{slice_stamp}.csv"
    csv_path    = out_dir / csv_name

    # ── write / append slice CSV ─────────────────────────────────────
    header_needed = not csv_path.exists()
    clean.to_csv(
        csv_path,
        mode="a",
        header=header_needed,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
    )

    # ── auxiliary exports ────────────────────────────────────────────
    append_datalogger(out_dir, point, sensor, clean)
    clean["TIMESTAMP"] = clean["TIMESTAMP"].dt.tz_localize(None)
    excel_path = out_dir / f"{point}_{sensor}_{run_date}.xlsx"
    write_excel(excel_path, clean, clean.describe().T.reset_index())

    make_pdf(clean, out_dir / f"{point}_{sensor}_{run_date}.pdf")

    # ── logging & return ─────────────────────────────────────────────
    logger.info(f"{point} SID={sensor} → {len(clean)} new rows")
    return clean["TIMESTAMP"].max().to_pydatetime()
