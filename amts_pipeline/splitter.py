"""
Simple splitter:
    * watches one export folder for Integrity-Monitor style CSVs
    * matches every file against FileProfiles
    * splits each row into per-point CSVs under SeparatedRoot
    * moves the original CSV to  <ExportRoot>/archive/  (same file-name)

Usage
-----
    python -m amts_pipeline.splitter_simple \
           --export-root   "C:/T4D_Export/PapeSOE_TTC" \
           --separated-root "D:/Separated" \
           [--once] [--sleep 60]

    --once   do one pass and exit
    --sleep  seconds between passes (default 60)
"""
from __future__ import annotations

import argparse
import glob
import shutil
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from .file_profiles import get_profile, list_profile_names, validate_timezone
from .log_utils     import get_logger

LOG = get_logger(__name__)


# ───────────────────────── CLI ──────────────────────────
def _cli() -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="simple-splitter")
    ap.add_argument("--export-root",    required=True, help="folder with raw CSVs")
    ap.add_argument("--separated-root", required=True, help="where per-point CSVs go")
    ap.add_argument("--once",  action="store_true", help="process once and exit")
    ap.add_argument("--sleep", type=int, default=60, help="delay between loops [60 s]")
    return ap.parse_args()


# ───────────────────────── helpers ─────────────────────
def _iso_from_name(stem: str) -> str:
    """extract YYYYMMDD_HHMMSS from …_20250311_200102_UTC.csv -> ISO string"""
    try:
        part = stem.rsplit("_", 2)[1]
        return datetime.strptime(part, "%Y%m%d_%H%M%S").strftime("%Y-%m-%dT%H%M%SZ")
    except Exception:
        return "unknown"


def _split_one(csv_path: Path,
               prof: dict[str, str],
               separated_root: Path) -> bool:
    """Return True on success; log+False on error."""
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as exc:
        LOG.error("❌  cannot read %s (%s)", csv_path.name, exc)
        return False

    # column names from profile ─────────────────────────
    col_p = prof.get("ColumnPoint",    "Point Name")
    col_t = prof.get("ColumnTime",     "Event Time (UTC)")
    col_n = prof.get("ColumnNorthing", "Northing")
    col_e = prof.get("ColumnEasting",  "Easting")
    col_h = prof.get("ColumnElevation","Elevation")

    if any(c not in df.columns for c in (col_p, col_t, col_h)):
        LOG.error("❌  %s missing mandatory columns", csv_path.name)
        return False

    df = df.rename(columns={
        col_p: "POINT_RAW",
        col_t: "LOCAL_TIME",
        col_n: "Northing",
        col_e: "Easting",
        col_h: "Elevation",
    })

    tz = validate_timezone(prof.get("TimeZone")) or "UTC"
    try:
        df["TIMESTAMP"] = (
            pd.to_datetime(df["LOCAL_TIME"], errors="coerce")
              .dt.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
              .dt.tz_convert("UTC")
        )
    except Exception as exc:
        LOG.error("❌  %s cannot convert times (%s)", csv_path.name, exc)
        return False

    stem = csv_path.stem.rsplit("_", 2)[0]      # Integrity Monitor [OLS_KB04]
    iso  = _iso_from_name(csv_path.stem)

    for pnt, sub in df.groupby("POINT_RAW"):
        folder = separated_root / f"{stem}_{pnt}"
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / f"{stem}_{pnt}_{iso}.csv"
        try:
            sub.to_csv(out, index=False,
                       date_format="%Y-%m-%d %H:%M:%S")
            LOG.info("✔︎ %s -> %s (%d rows)", csv_path.name, out.name, len(sub))
        except Exception as exc:
            LOG.error("❌  %s cannot write %s (%s)", csv_path.name, out.name, exc)
            return False

    return True


def _cycle(export_root: Path, separated_root: Path) -> None:
    profiles = {n: get_profile(n) for n in list_profile_names()}

    for prof in profiles.values():
        if prof is None:
            continue
        for fp in glob.glob(str(export_root / prof["Match"])):
            f = Path(fp)
            if (export_root / "archive" / f.name).exists():
                # already moved → skip
                continue

            ok = _split_one(f, prof, separated_root)
            if ok:
                archive = export_root / "archive" / f.name
                archive.parent.mkdir(exist_ok=True)
                try:
                    shutil.move(fp, archive)
                except Exception as exc:
                    LOG.warning("Could not move %s to archive (%s)", f.name, exc)


def main() -> None:
    ns = _cli()
    root_in  = Path(ns.export_root).resolve()
    root_out = Path(ns.separated_root).resolve()

    LOG.info(" watching  %s", root_in)
    LOG.info(" writing   %s", root_out)
    LOG.info(" archive   %s\\archive", root_in)

    def loop_once() -> None:
        _cycle(root_in, root_out)

    if ns.once:
        loop_once()
    else:
        while True:
            loop_once()
            time.sleep(ns.sleep)


if __name__ == "__main__":
    main()
