"""
amts_pipeline.file_profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Lazy loader for the “FileProfiles” worksheet inside Settings.xlsx.

Mandatory columns:
    • Profile  – unique key referenced from Settings sheet
    • Match    – glob pattern, e.g.  Integrity Monitor [OLS_OG04A]*.csv
Everything else is optional.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, cast
import functools
import logging
import zoneinfo

import pandas as pd

ROOT          = Path(__file__).resolve().parent.parent
SETTINGS_BOOK = ROOT / "Settings.xlsx"        # one workbook, two sheets
_SHEET_NAME   = "FileProfiles"

_log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _profile_df() -> pd.DataFrame:
    """Read and cache *FileProfiles* sheet – never raises, always a DataFrame."""
    try:
        df = pd.read_excel(SETTINGS_BOOK, sheet_name=_SHEET_NAME, engine="openpyxl")
    except ValueError as e:                       # sheet name not found
        _log.error("%s – worksheet “%s” not found, returning empty DF", SETTINGS_BOOK, _SHEET_NAME)
        return pd.DataFrame()
    except ImportError as e:                      # openpyxl missing
        _log.error(
            "⚠  openpyxl is required to read %s – run `pip install \"openpyxl>=3.1\"`",
            SETTINGS_BOOK,
        )
        return pd.DataFrame()
    except Exception as exc:                      # any other I/O/parse issue
        _log.error("Could not read %s › %s – %s", SETTINGS_BOOK, _SHEET_NAME, exc)
        return pd.DataFrame()

    # minimal sanity: drop blank rows, require Profile & Match
    df = df.dropna(how="all")
    df = df.dropna(subset=["Profile", "Match"])

    # ensure uniqueness of the key
    if df["Profile"].duplicated().any():
        dupes = df[df["Profile"].duplicated()]["Profile"].tolist()
        _log.warning("Duplicate FileProfile rows %s – keeping first occurence", dupes)
        df = df.drop_duplicates(subset=["Profile"], keep="first")

    return df.set_index("Profile")   # look-ups by key are fast now


# ───────────────────────── public helpers ─────────────────────────────────
def get_profile(name: str) -> Dict[str, str] | None:
    try:
        ser = _profile_df().loc[name].dropna()
        # convert both keys & values to plain str
        coerced = {str(k): str(v) for k, v in ser.items()}
        return cast(Dict[str, str], coerced)      # tell the type-checker
    except KeyError:
        _log.error("FileProfile “%s” not found – check the sheet name/typo", name)
        return None


def list_profile_names() -> List[str]:
    return _profile_df().index.tolist()


def validate_timezone(tz: str | None) -> str | None:
    """Return *tz* if it’s a valid Olson name, else log + return **None**."""
    if not tz:
        return None
    try:
        zoneinfo.ZoneInfo(str(tz))
        return str(tz)
    except Exception:
        _log.warning("Invalid TimeZone “%s” in FileProfiles – defaulting to UTC", tz)
        return None