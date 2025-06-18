"""Process one Settings slice: load raw → MAD filter → delta → outputs."""
from __future__ import annotations
import pandas as pd, numpy as np
from datetime import datetime, timezone
from pathlib import Path
from .mad_utils import mad_filter
from .io_utils import load_raw_csvs, append_datalogger, write_excel
from .plotting import make_pdf
from .log_utils import get_logger

logger = get_logger()


def process_slice(row: pd.Series, latest_ts):
    point, sensor, site = row["PointName"], row["SensorID"], row["Site"]
    import_dir = Path(row["ImportFolder"]).expanduser()
    start_utc = pd.to_datetime(row["StartUTC"], utc=True)
    raw = load_raw_csvs(import_dir)
    if raw.empty:
        logger.warning(f"{point} SID={sensor} – no raw data")
        return None

    raw["TIMESTAMP"] = pd.to_datetime(raw["Event Time (Eastern Standard Time)"], errors="coerce")
    raw = raw.dropna(subset=["TIMESTAMP"])
    raw = raw[raw["TIMESTAMP"].dt.tz_convert(timezone.utc) >= start_utc]
    if latest_ts is not None:
        raw = raw[raw["TIMESTAMP"] > latest_ts]
    if raw.empty:
        return None

    cols = ["Elevation"] if row["Type"].lower()=="reflectless" else ["Northing","Easting","Elevation"]
    baselines = {"Northing": row["BaselineN"], "Easting": row["BaselineE"], "Elevation": row["BaselineH"]}
    clean = mad_filter(raw, cols, row["OutlierMAD"], baselines)

    clean["Delta_H_mm"] = (clean["Elevation"]-float(row["BaselineH"]))*1000
    if row["Type"].lower()=="reflective":
        clean["Delta_N_mm"] = (clean["Northing"]-float(row["BaselineN"]))*1000
        clean["Delta_E_mm"] = (clean["Easting"]-float(row["BaselineE"]))*1000

    # write slice CSV (append mode)
    site_root = Path(row["ExportFolder"] or row["ImportFolder"])
    run_date = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = site_root / site / run_date / point
    out_dir.mkdir(parents=True, exist_ok=True)
    slice_stamp = start_utc.strftime("%Y%m%dT%H%M%SZ")
    csv_name = f"{point}_{sensor}_{slice_stamp}.csv"
    header = not (out_dir/csv_name).exists()
    clean.to_csv(out_dir/csv_name, mode="a", header=header, index=False, date_format="%Y-%m-%d %H:%M:%S")

    # data‑logger append (ΔH only)
    append_datalogger(out_dir, point, sensor, clean)

    # Excel summary (once per day)
    excel_path = out_dir / f"{point}_{sensor}_{run_date}.xlsx"
    write_excel(excel_path, clean, clean.describe().T.reset_index())

    # plot PDF
    make_pdf(clean, out_dir/ f"{point}_{sensor}_{run_date}.pdf")

    logger.info(f"{point} SID={sensor} → {len(clean)} new rows")
    return clean["TIMESTAMP"].max().to_pydatetime()