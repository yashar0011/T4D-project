from __future__ import annotations
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import pandas as pd
import io, asyncio, os

from .models import DeltasResponse, SettingsRow, SettingsUpdate, CommandRequest
from .deps import get_settings, load_deltas, SETTINGS_PATH
from .watcher_runner import CMD_Q

router = APIRouter(prefix="/api", tags=["api"])


# ───────────────────────── deltas ────────────────────────────
@router.get("/deltas", response_model=DeltasResponse)
async def get_deltas(point: str, hours: int = 24):
    df = load_deltas(point, hours)
    if df.empty:
        raise HTTPException(404, "no data")
    return {"point": point, "rows": df.to_dict("records")}


# ───────────────────────── settings ──────────────────────────
@router.get("/settings", response_model=list[SettingsRow])
async def list_settings():
    df = get_settings().reset_index().rename(columns={"index": "id"})
    return df.to_dict("records")

@router.put("/settings/{row_id}")
async def patch_setting(row_id: int, upd: SettingsUpdate):
    df = get_settings()
    if row_id >= len(df):
        raise HTTPException(404, "row not found")
    df.at[row_id, upd.field] = upd.value
    df.to_excel(SETTINGS_PATH, index=False)
    CMD_Q.put("run_once")
    return {"status": "ok"}


# ─────────────────────── outputs browser ─────────────────────
BASE_OUTPUT = Path(os.getenv("T4D_OUTPUT_ROOT", "D:/DispAMTS"))

@router.get("/outputs/sites")
async def list_sites():
    return [p.name for p in BASE_OUTPUT.iterdir() if p.is_dir()]

@router.get("/outputs/tree")
async def tree(path: str):
    full = BASE_OUTPUT / path
    if not full.exists():
        raise HTTPException(404)
    return [p.name for p in full.iterdir()]

@router.get("/outputs/file")
async def download(path: str):
    full = BASE_OUTPUT / path
    if not full.exists():
        raise HTTPException(404)
    return FileResponse(full)


# ───────────────────────── logs tail ─────────────────────────
@router.get("/logs")
async def tail(site: str, lines: int = 200):
    log_file = BASE_OUTPUT / site / "logs" / f"{pd.Timestamp.utcnow():%Y%m%d}.log"
    if not log_file.exists():
        raise HTTPException(404)
    with open(log_file, "rb") as fh:
        tail_bytes = fh.readlines()[-lines:]
    content = b"".join(tail_bytes)
    return StreamingResponse(io.BytesIO(content), media_type="text/plain")


# ─────────────────────── pipeline control ────────────────────
@router.post("/command")
async def command(cmd: CommandRequest):
    if cmd.stop:
        CMD_Q.put("stop")
    elif cmd.full_build:
        CMD_Q.put("full_build")
    elif cmd.run_once:
        CMD_Q.put("run_once")
    else:
        raise HTTPException(400, "no command flag set")
    return {"queued": True}