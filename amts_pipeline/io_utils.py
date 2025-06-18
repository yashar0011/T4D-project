"""I/O helpers: raw load, Excel writer, Data‑Logger exporter."""
from __future__ import annotations
import pandas as pd
from pathlib import Path
from datetime import datetime

DT_FMT = "%Y-%m-%d %H:%M:%S"


def load_raw_csvs(folder: Path):
    parts = []
    for f in folder.glob("*.csv"):
        try:
            df = pd.read_csv(f, parse_dates=["Event Time (Eastern Standard Time)"])
            parts.append(df)
        except Exception:
            pass
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def append_datalogger(out_folder: Path, point: str, sensor: str, df: pd.DataFrame):
    """Write/append Data‑Logger‑style two‑column CSV (TIMESTAMP,VALUE)."""
    out_folder.mkdir(parents=True, exist_ok=True)
    out_path = out_folder / f"{point}_{sensor}_dl.csv"
    header = not out_path.exists()
    df[["TIMESTAMP","Delta_H_mm"]].to_csv(out_path, mode="a", header=header,
                                            index=False, date_format=DT_FMT)


def write_excel(excel_path: Path, combined_df: pd.DataFrame, summary_df: pd.DataFrame):
    import xlsxwriter
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as xw:
        combined_df.to_excel(xw, sheet_name="Combined", index=False)
        summary_df.to_excel(xw, sheet_name="Summary", index=False)