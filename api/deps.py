"""Thin helper wrappers around amts_pipeline so routes don’t import internals."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

from amts_pipeline.settings import load_active_settings
from amts_pipeline.io_utils import load_raw_csvs
from amts_pipeline.cleaner import mad_filter

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "Settings.xlsx"


def get_settings_df() -> pd.DataFrame:
    return load_active_settings(SETTINGS_PATH)


def list_sites() -> list[str]:
    df = get_settings_df()
    return sorted(df["Site"].unique().tolist())


def load_deltas(point: str, hours: int) -> pd.DataFrame:
    df = get_settings_df()
    row = df[df["PointName"] == point].iloc[0]
    export_root = Path(row["ExportFolder"] or row["ImportFolder"])
    site_dir = export_root / row["Site"]
    dfs: list[pd.DataFrame] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for day_dir in site_dir.rglob("*/" + point):
        for csv in day_dir.glob("*_dl.csv"):
            tmp = pd.read_csv(csv, parse_dates=["TIMESTAMP"])
            dfs.append(tmp)
    if not dfs:
        return pd.DataFrame()
    big = pd.concat(dfs, ignore_index=True)
    return big[big["TIMESTAMP"] >= cutoff]