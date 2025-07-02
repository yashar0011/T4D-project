# amts_pipeline/settings.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import pandas as pd

ROOT: Final = Path(__file__).resolve().parent.parent
SETTINGS_XLSX: Final = ROOT / "Settings.xlsx"
_LOG = logging.getLogger(__name__)


# ───────────────────────── row-level sanity checks ──────────────────────────
def _validate_row(row: pd.Series) -> None:
    """
    • Ensure **Type** is either Reflective or Reflectless  
    • If Type == Reflective, BaselineN & BaselineE must be present
    • OutlierMAD → positive float (defaults handled later)
    """
    pnt = row["PointName"]

    # 1) Type
    t = str(row["Type"]).strip().lower()
    if t not in {"reflective", "reflectless"}:
        raise ValueError(f"{pnt}: unknown Type {row['Type']!r}")

    # 2) Baselines
    if t == "reflective":
        if pd.isna(row.get("BaselineN")) or pd.isna(row.get("BaselineE")):
            raise ValueError(f"{pnt}: Reflective points need BaselineN & BaselineE")
    if pd.isna(row.get("BaselineH")):
        raise ValueError(f"{pnt}: BaselineH is required")

    # 3) OutlierMAD
    mad = row.get("OutlierMAD", 3.5)
    if not (isinstance(mad, (int, float)) and mad > 0):
        raise ValueError(f"{pnt}: OutlierMAD must be a positive number")


# ───────────────────────── public helper ────────────────────────────────────
def load_active_settings(path: Path = SETTINGS_XLSX) -> pd.DataFrame:
    """
    Read the **Settings** worksheet, keep rows where CSVImport == TRUE,
    run per-row sanity checks, and return the cleaned DataFrame.

    Any invalid row raises **ValueError** so problems are caught at start-up
    instead of half-way through a job.
    """
    try:
        df = pd.read_excel(path, sheet_name="Settings")
    except Exception as exc:
        raise RuntimeError(f"Cannot read {path} › Settings – {exc}") from exc

    # robust boolean cast (TRUE/False/1/0/Yes/No…)
    active_mask = df["CSVImport"].astype(str).str.lower().isin(
        {"true", "1", "yes", "y"}
    )
    df = df.loc[active_mask].copy()

    # validation
    for _, row in df.iterrows():
        _validate_row(row)

    _LOG.info("Loaded %d active Settings rows from %s", len(df), path.name)
    return df.reset_index(drop=True)
