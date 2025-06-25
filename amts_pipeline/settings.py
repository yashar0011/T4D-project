"""
Load *Settings.xlsx* and return **only** the rows that are meant to be
processed (CSVImport = TRUE).  All other logic (parsing of types, date
columns, etc.) lives here so the rest of the pipeline can rely on a clean
DataFrame.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd


def _coerce_bool(col: pd.Series) -> pd.Series:
    """Accept TRUE/FALSE, 1/0, 'yes'/'no', etc. – default False."""
    return (
        col.fillna(False)
           .astype(str)
           .str.strip()
           .str.lower()
           .isin({"true", "1", "yes"})
    )


def load_active_settings(path: Path | str) -> pd.DataFrame:
    df = pd.read_excel(path)

    # --- normalise new boolean flags ----------------------------------------
    for flag in ("CSVImport", "SQLImport"):
        if flag not in df.columns:
            raise ValueError(f"Missing required column “{flag}” in {path}")
        df[flag] = _coerce_bool(df[flag])

    # keep ONLY points that should be processed (CSVImport = TRUE)
    df = df[df["CSVImport"]].copy()

    # make sure numeric columns have numeric dtypes
    numeric_cols = [
        "SQLSensorID", "BaselineN", "BaselineE", "BaselineH", "OutlierMAD"
    ]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="raise")

    # parse the UTC start date
    df["StartUTC"] = pd.to_datetime(df["StartUTC"], utc=True)

    # always sort by PointName for reproducibility
    return df.sort_values("SQLSensorID").reset_index(drop=True)