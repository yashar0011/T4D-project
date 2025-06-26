# amts_pipeline/settings.py
from __future__ import annotations
from pathlib import Path
import pandas as pd

SETTINGS_XLSX = Path(__file__).resolve().parent.parent / "Settings.xlsx"

# ───────────────────────── helpers ──────────────────────────
def _validate_row(r: pd.Series) -> None:
    """Ensure CalculationType ↔︎ TerrestrialColumnName are compatible."""
    cols = [c.strip().title() for c in str(r["TerrestrialColumnName"]).split("|")]
    calc = str(r["CalculationType"]).strip().lower()

    allowed = {
        "reflective":  {"Elevation", "Northing", "Easting"},
        "reflectless": {"Elevation"},
    }

    if calc not in allowed:
        raise ValueError(f"{r['PointName']}: unknown CalculationType {r['CalculationType']!r}")

    # Reflective must have at least Elevation; if vector cols present, require all 3
    needed = allowed[calc]
    if not set(cols).issubset(needed):
        raise ValueError(
            f"{r['PointName']}: columns {cols} incompatible with {r['CalculationType']}"
        )

def load_active_settings(path: Path = SETTINGS_XLSX) -> pd.DataFrame:
    """Read sheet, run per-row validation, return ACTIVE rows only."""
    df = pd.read_excel(path, sheet_name="Settings")
    df = df.loc[df["CSVImport"].astype(bool)].copy()      # ← your new on/off flag

    # validate up-front so bad rows never reach the pipeline
    for _, row in df.iterrows():
        _validate_row(row)

    return df
