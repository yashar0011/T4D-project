"""
Simple splitter:
    * watches one export folder for Integrity-Monitor style CSVs
    * matches every file against FileProfiles
    * splits each row into per-point CSVs under SeparatedRoot
    * moves the original CSV to  <ExportRoot>/archive/  (same file-name)
    * moves any failed CSVs to <ExportRoot>/quarantine/ (same file-name)

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
import logging # Make sure logging is imported at the top level

# This script assumes you have pandas installed (pip install pandas)
try:
    import pandas as pd
except ImportError:
    print("Error: pandas is not installed. Please install it using 'pip install pandas'")
    exit()

# It also assumes the local utility modules (file_profiles, log_utils) are available.
try:
    from .file_profiles import (
        get_profile,
        list_profile_names,
        validate_timezone,
    )
    from .log_utils import get_logger
except ImportError:
    # This block allows the script to run even without the custom local modules.
    # It provides basic functionality for logging and profiles.

    # FIX: The mock function must have a signature consistent with the real one.
    # The 'level' parameter should be an integer from the logging module.
    def get_logger(name: str, level=logging.INFO, site_root: Path | None = None):
        """Mock logger function for standalone execution."""
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(name)
        # Add a dummy argument to match the real function signature if needed
        # This function doesn't use site_root, but having it makes it compatible.
        if site_root:
            logger.info(f"Mock logger: site_root '{site_root}' would be used here.")
        return logger

    def list_profile_names():
        """Mock profile names function."""
        return ["default"]

    def get_profile(name):
        """Mock profile getter function."""
        if name == "default":
            return {
                "Match": "*.csv",
                "ColumnPoint": "Point Name",
                "ColumnTime": "Event Time (UTC)",
                "ColumnNorthing": "Northing",
                "ColumnEasting": "Easting",
                "ColumnElevation": "Elevation",
                "TimeZone": "UTC",
            }
        return None

    def validate_timezone(tz):
        """Mock timezone validator."""
        return tz if tz in ["UTC", "America/New_York"] else "UTC"


# Use the integer logging level, not a string.
LOG = get_logger(__name__, level=logging.DEBUG)

# ───────────────────────── CLI ──────────────────────────
def _cli() -> argparse.Namespace:
    """Parses command-line arguments."""
    ap = argparse.ArgumentParser(
        description="Watches a folder for CSVs, splits them by point, and archives them.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    ap.add_argument("--export-root",    required=True, help="Folder with raw CSVs to monitor.")
    ap.add_argument("--separated-root", required=True, help="Root folder where per-point CSVs will be saved.")
    ap.add_argument("--once",   action="store_true", help="Run the process once and then exit.")
    ap.add_argument("--sleep", type=int, default=60, help="Delay in seconds between processing loops [default: 60].")
    return ap.parse_args()


# ───────────────────────── helpers ─────────────────────
def _iso_from_name(stem: str) -> str:
    """
    Extracts YYYYMMDD_HHMMSS from a filename stem and converts it to an ISO 8601 string.
    Example: '..._20250311_200102_UTC' -> '2025-03-11T200102Z'
    """
    try:
        parts = stem.rsplit("_", 3)
        date_time_part = f"{parts[-3]}_{parts[-2]}"
        dt_obj = datetime.strptime(date_time_part, "%Y%m%d_%H%M%S")
        return dt_obj.strftime("%Y-%m-%dT%H%M%SZ")
    except (ValueError, IndexError):
        LOG.warning("Could not parse timestamp from filename stem: '%s'. Using 'unknown'.", stem)
        return "unknown"


def _split_one(csv_path: Path, prof: dict[str, str], separated_root: Path) -> bool:
    """
    Splits a single CSV file into multiple CSVs, one for each unique point.
    Returns True on success, False on failure.
    """
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as exc:
        LOG.error("❌ Cannot read '%s': %s", csv_path.name, exc)
        return False

    col_p = prof.get("ColumnPoint",    "Point Name")
    col_t = prof.get("ColumnTime",     "Event Time (UTC)")
    col_h = prof.get("ColumnElevation","Elevation")

    required_cols = {col_p, col_t, col_h}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        LOG.error("❌ '%s' is missing mandatory columns: %s", csv_path.name, ', '.join(missing))
        return False

    df = df.rename(columns={
        prof.get("ColumnPoint", "Point Name"): "POINT_RAW",
        prof.get("ColumnTime", "Event Time (UTC)"): "LOCAL_TIME",
        prof.get("ColumnNorthing", "Northing"): "Northing",
        prof.get("ColumnEasting", "Easting"): "Easting",
        prof.get("ColumnElevation", "Elevation"): "Elevation",
    })

    tz = validate_timezone(prof.get("TimeZone")) or "UTC"
    try:
        datetimes = pd.to_datetime(df["LOCAL_TIME"], errors="coerce")
        df["TIMESTAMP"] = (
            datetimes.dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
                     .dt.tz_convert("UTC")
        )
        if df["TIMESTAMP"].isnull().any():
            LOG.warning("⚠︎ Some timestamps in '%s' could not be parsed and were ignored.", csv_path.name)
    except Exception as exc:
        LOG.error("❌ Could not convert timestamps in '%s': %s", csv_path.name, exc)
        return False

    try:
        stem = csv_path.stem.rsplit("_", 3)[0]
    except IndexError:
        stem = csv_path.stem
    iso  = _iso_from_name(csv_path.stem)

    for pnt, sub_df in df.groupby("POINT_RAW"):
        sanitized_pnt = "".join(c for c in str(pnt) if c.isalnum() or c in ('-', '_')).rstrip()
        folder = separated_root / f"{stem}_{sanitized_pnt}"
        folder.mkdir(parents=True, exist_ok=True)
        
        out_path = folder / f"{stem}_{sanitized_pnt}_{iso}.csv"
        try:
            output_df = sub_df[["TIMESTAMP", "Northing", "Easting", "Elevation"] + [c for c in sub_df.columns if c not in ["POINT_RAW", "LOCAL_TIME", "TIMESTAMP", "Northing", "Easting", "Elevation"]]]
            output_df.to_csv(out_path, index=False, date_format="%Y-%m-%d %H:%M:%S")
            LOG.info("✔︎ Split %s -> %s (%d rows)", csv_path.name, out_path.name, len(sub_df))
        except Exception as exc:
            LOG.error("❌ Failed to write '%s': %s", out_path.name, exc)
            return False

    return True


def _cycle(export_root: Path, separated_root: Path) -> None:
    """Performs one full processing cycle over the export_root directory."""
    profiles = {name: get_profile(name) for name in list_profile_names()}
    archive_dir = export_root / "archive"
    quarantine_dir = export_root / "quarantine"

    for name, prof in profiles.items():
        if prof is None:
            LOG.warning("⚠︎ Profile '%s' is invalid or returned None. Check settings.", name)
            continue

        pattern = str(export_root / prof["Match"])
        try:
            files = sorted(Path(p) for p in glob.glob(pattern))
        except Exception:
            LOG.error("Invalid pattern in profile '%s': %s", name, prof["Match"])
            continue

        LOG.debug("Profile '%s': pattern '%s' matched %d file(s)", name, prof["Match"], len(files))

        for f in files:
            if f.parent.name in ("archive", "quarantine"):
                continue
            
            LOG.debug("→ Inspecting '%s'", f.name)
            
            try:
                ok = _split_one(f, prof, separated_root)
                if ok:
                    archive_dir.mkdir(exist_ok=True)
                    shutil.move(str(f), archive_dir / f.name)
                    LOG.info("📦 Archived '%s'", f.name)
                else:
                    quarantine_dir.mkdir(exist_ok=True)
                    shutil.move(str(f), quarantine_dir / f.name)
                    LOG.warning("🗄️ Quarantined failing file '%s'", f.name)
            except Exception as exc:
                LOG.error("❌ Unhandled error on '%s': %s", f.name, exc, exc_info=True)
                try:
                    quarantine_dir.mkdir(exist_ok=True)
                    shutil.move(str(f), quarantine_dir / f.name)
                    LOG.warning("🗄️ Quarantined '%s' after unhandled error.", f.name)
                except Exception as move_exc:
                    LOG.error("Could not quarantine '%s': %s", f.name, move_exc)


def main() -> None:
    """Main execution function."""
    ns = _cli()
    try:
        root_in  = Path(ns.export_root).resolve(strict=True)
        root_out = Path(ns.separated_root)
        root_out.mkdir(parents=True, exist_ok=True)
    except FileNotFoundError:
        LOG.error("Error: The export root directory does not exist: %s", ns.export_root)
        return
    except Exception as e:
        LOG.error("Error setting up directories: %s", e)
        return

    LOG.info("─" * 50)
    LOG.info("▶︎ Starting Simple Splitter")
    LOG.info("  Watching   : %s", root_in)
    LOG.info("  Writing to : %s", root_out)
    LOG.info("  Archive    : %s", root_in / "archive")
    LOG.info("  Quarantine : %s", root_in / "quarantine")
    LOG.info("─" * 50)

    if ns.once:
        _cycle(root_in, root_out)
        LOG.info("✓ Run --once complete.")
    else:
        LOG.info("Entering monitoring loop... Press Ctrl+C to exit.")
        try:
            while True:
                _cycle(root_in, root_out)
                LOG.debug("Sleeping for %d seconds...", ns.sleep)
                time.sleep(ns.sleep)
        except KeyboardInterrupt:
            LOG.info("\n🛑 User interrupted. Shutting down.")
        except Exception as e:
            LOG.error("An unexpected error occurred in the main loop: %s", e)


if __name__ == "__main__":
    main()