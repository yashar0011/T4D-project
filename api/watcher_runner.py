"""Background thread that runs amts_pipeline.watcher.start_watch() and
   exposes a queue for control commands."""
from __future__ import annotations
import threading, queue, subprocess, sys, time, logging
from pathlib import Path
from amts_pipeline.watcher import start_watch

log = logging.getLogger("watcher_runner")

CMD_Q: queue.Queue[str] = queue.Queue()

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "Settings.xlsx"


def _watch_loop():
    while True:
        try:
            cmd = CMD_Q.get_nowait()
            if cmd == "stop":
                log.info("watcher thread received stop")
                break
            elif cmd == "run_once":
                log.info("running incremental pass…")
                subprocess.run([sys.executable, "-m", "amts_pipeline", "--run-once"], check=True)
            elif cmd == "full_build":
                log.info("running full rebuild…")
                subprocess.run([sys.executable, "-m", "amts_pipeline", "--run-once", "--full"], check=True)
        except queue.Empty:
            # idle; fastapi thread handles main watcher block
            time.sleep(0.5)


def start_background_thread():
    t = threading.Thread(target=start_watch, args=(SETTINGS_PATH,), kwargs={"force_full": False}, daemon=True)
    t.start()
    ctl = threading.Thread(target=_watch_loop, daemon=True)
    ctl.start()