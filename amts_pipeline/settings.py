"""Load & validate Settings.xlsx / CSV."""
from __future__ import annotations
import pandas as pd
from pathlib import Path

KEY_COLS = [
    "Active","SensorID","Site","PointName","Type","ImportFolder","ExportFolder",
    "BaselineN","BaselineE","BaselineH","OutlierMAD","StartUTC"
]


def load_active_settings(path: Path):
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]
    for c in KEY_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[df.Active.astype(str).str.upper() == "TRUE"].copy()
    df.sort_values(["SensorID","PointName","StartUTC"], inplace=True)
    return df[KEY_COLS]