#!/usr/bin/env python
"""
run.py – friendly launcher for the AMTS toolbox
==============================================
"""

from __future__ import annotations
import subprocess, sys, textwrap
from pathlib import Path

# ────────────────────────── helpers ──────────────────────────
def _ask_path(msg: str, default: str | None = None, *, must_exist=True) -> Path:
    while True:
        raw = input(f"{msg}{' ['+default+']' if default else ''}: ").strip() or default
        if not raw:
            print("  ✖ please enter a path")
            continue
        p = Path(raw).expanduser()
        if must_exist and not p.exists():
            print(f"  ✖ {p} does not exist")
        else:
            return p

def _ask_int(msg: str, default: int) -> int:
    while True:
        raw = input(f"{msg} [{default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit():
            return int(raw)
        print("  ✖ not a number")

def _spawn(cmd: list[str]) -> None:
    print("\n▶", " ".join(cmd), "\n")
    subprocess.run(cmd, check=True)

# ────────────────────────── tasks ────────────────────────────
def split_loop(single_pass: bool) -> None:
    exp = _ask_path("Export folder with raw T4D CSVs")
    sep = _ask_path("Separated-CSV folder", "D:/Separated", must_exist=False)
    sleep = 0 if single_pass else _ask_int("Seconds between passes", 60)

    cmd = [
        sys.executable, "-m", "amts_pipeline.splitter",
        "--export-root", str(exp),
        "--separated-root", str(sep),
    ]
    cmd += ["--once"] if single_pass else ["--sleep", str(sleep)]
    _spawn(cmd)

def run_watcher(full: bool) -> None:
    settings = _ask_path("Path to Settings.xlsx", "Settings.xlsx")
    cmd = [
        sys.executable, "-m", "amts_pipeline.watcher",
        "--settings", str(settings)            # ← FIX: pass with flag
    ]
    if full:
        cmd.append("--full")
    _spawn(cmd)

# ────────────────────────── menu ─────────────────────────────
def main() -> None:
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
            case "5" | "": print("Bye!"); return
            case _: print("✖ unknown choice")

if __name__ == "__main__":
    main()
