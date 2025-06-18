"""CLI entry‑point: handles --full flag and default Settings.xlsx lookup."""
import sys, argparse
from pathlib import Path
from .watcher import start_watch
from .log_utils import get_logger

logger = get_logger()

def _default_settings():
    here = Path(__file__).resolve().parent
    default = here.parent / "Settings.xlsx"
    return default if default.exists() else None

def main():
    parser = argparse.ArgumentParser(description="AMTS time‑sliced MAD pipeline")
    parser.add_argument("settings", nargs="?", help="Path to Settings.xlsx/CSV")
    parser.add_argument("--full", action="store_true", help="Rebuild all slices")
    args = parser.parse_args()

    settings_path = Path(args.settings).resolve() if args.settings else _default_settings()
    if not settings_path or not settings_path.exists():
        logger.error("Settings file not found. Provide a path or place Settings.xlsx next to the package.")
        sys.exit(1)

    start_watch(settings_path, force_full=args.full)

if __name__ == "__main__":
    main()