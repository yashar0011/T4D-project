#!/usr/bin/env python
"""
run.py – friendly launcher for the AMTS toolbox
==============================================

Just run::

    python run.py
"""
from __future__ import annotations
from pathlib import Path
import sys
import textwrap
import time

# --- Direct Imports from the pipeline ---
# This is the correct way to use functions from other modules in the same project.
# It avoids creating subprocesses and prevents the RuntimeWarning.
from amts_pipeline.watcher import start_watch
from amts_pipeline.splitter import _cycle as splitter_cycle


# ─────────────────────────────────────────────────────────────────────────────
def _ask_path(msg: str, default: str | None = None, must_exist=True) -> Path:
    """Helper function to prompt the user for a valid path."""
    while True:
        raw = input(f"{msg}{' ['+default+']' if default else ''}: ").strip() or default
        if not raw:
            print("  ✖ please enter a path")
            continue
        p = Path(raw).expanduser().resolve()
        if must_exist and not p.exists():
            print(f"  ✖ {p} does not exist")
        else:
            return p

def _ask_int(msg: str, default: int) -> int:
    """Helper function to prompt the user for an integer."""
    while True:
        raw = input(f"{msg} [{default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit():
            return int(raw)
        print("  ✖ not a number")

# ─────────────────────────────────────────────────────────────────────────────
def split_loop(single_pass: bool) -> None:
    """Gets parameters and runs the splitter cycle."""
    exp = _ask_path("Export folder with raw T4D CSVs")
    sep = _ask_path("Separated-CSV folder", "D:/Separated", must_exist=False)
    
    if not sep.exists():
        sep.mkdir(parents=True)

    if single_pass:
        print("\n▶ Running splitter for a single pass...\n")
        splitter_cycle(exp, sep)
        print("\n✔︎ Single pass complete.")
    else:
        sleep = _ask_int("Seconds between passes", 60)
        print(f"\n▶ Starting splitter, checking every {sleep} seconds (Ctrl-C to stop)...\n")
        try:
            while True:
                splitter_cycle(exp, sep)
                time.sleep(sleep)
        except KeyboardInterrupt:
            print("\nSplitter stopped by user.")


def run_watcher(full: bool) -> None:
    """
    Gets parameters and runs the pipeline watcher.
    THIS IS THE CORRECTED FUNCTION. It calls start_watch directly.
    """
    settings = _ask_path("Path to Settings.xlsx", "Settings.xlsx")
    print(f"\n▶ Starting pipeline watcher (full_rebuild={full})...\n")
    # Directly call the imported function instead of using subprocess
    start_watch(settings, force_full=full)


def main() -> None:
    """Displays the main menu and executes the chosen task."""
    menu = textwrap.dedent("""
        Choose a task
        ─────────────
        1) Splitter – watch & split CSVs continuously
        2) Splitter – single pass then exit
        3) Pipeline watcher – process slices on Settings edits
        4) Pipeline – FULL rebuild now
        5) Quit
    """).strip()

    while True:
        choice = input(f"\n{menu}\n> ").strip()
        match choice:
            case "1": split_loop(False)
            case "2": split_loop(True)
            case "3": run_watcher(False)
            case "4": run_watcher(True)
            case "5" | "" | "q": print("Bye!"); return
            case _: print("✖ unknown choice")

if __name__ == "__main__":
    main()