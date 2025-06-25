# api/routes.py
# --------------------------------------------------------------------------- #
#  FastAPI routes – thin JSON layer that sits on top of the amts_pipeline
# --------------------------------------------------------------------------- #
from __future__ import annotations

import io, os
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse

from .deps import SETTINGS_PATH, get_settings, load_deltas
from .models import (
    CommandRequest,
    DeltasResponse,
    SettingsRow,
    SettingsUpdate,
)
from .watcher_runner import CMD_Q

router = APIRouter(prefix="/api", tags=["api"])

# --------------------------------------------------------------------------- #
#  /deltas – load the last N hours of Δ-CSV rows
# --------------------------------------------------------------------------- #


@router.get("/deltas", response_model=DeltasResponse)
async def get_deltas(
    point: str = Query(..., description="Exact PointName from Settings.xlsx"),
    hours: int = Query(
        24, ge=1, le=168, description="Look-back window (1-168 hours)"
    ),
):
    df = load_deltas(point, hours)
    # Never raise 4xx here – the React UI copes better with an empty array.
    return {"point": point, "rows": df.to_dict("records")}


# --------------------------------------------------------------------------- #
#  /points – convenience endpoint for the UI dropdown
# --------------------------------------------------------------------------- #


@router.get("/points", response_model=List[str])
async def list_points():
    """Return every active PointName in alphabetical order."""
    return sorted(get_settings()["PointName"].unique().tolist())


# --------------------------------------------------------------------------- #
#  /settings – read & patch the spreadsheet
# --------------------------------------------------------------------------- #


@router.get("/settings", response_model=List[SettingsRow])
async def list_settings():
    """Active rows as JSON-safe dicts (No NaN/Inf)."""
    df = (
        get_settings()
        .reset_index()
        .rename(columns={"index": "id"})
        .replace([np.inf, -np.inf], np.nan)
        .where(pd.notna, None)
    )
    return jsonable_encoder(df.to_dict("records"))


@router.put("/settings/{row_id}")
async def patch_setting(row_id: int, upd: SettingsUpdate):
    """Patch *one* cell in Settings.xlsx and trigger the watcher once."""
    df = get_settings()
    if row_id >= len(df):
        raise HTTPException(404, "row not found")

    if upd.field not in df.columns:
        raise HTTPException(400, f'unknown field “{upd.field}”')

    df.at[row_id, upd.field] = upd.value
    df.to_excel(SETTINGS_PATH, index=False)

    CMD_Q.put("run_once")  # tell watcher_runner to process immediately
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
#  Outputs browser – read-only file explorer
# --------------------------------------------------------------------------- #

_BASE_OUTPUT = Path(os.getenv("T4D_OUTPUT_ROOT", "D:/DispAMTS")).resolve()


def _safe_join(rel: str) -> Path:
    """Prevent “..” escapes and ensure path is under _BASE_OUTPUT."""
    full = (_BASE_OUTPUT / rel.lstrip("/")).resolve()
    if not str(full).startswith(str(_BASE_OUTPUT)):
        raise HTTPException(400, "illegal path")
    return full


@router.get("/outputs/sites", response_model=List[str])
async def outputs_sites():
    return sorted(p.name for p in _BASE_OUTPUT.iterdir() if p.is_dir())


@router.get("/outputs/tree", response_model=List[str])
async def outputs_tree(path: str = Query("")):
    full = _safe_join(path)
    if not full.is_dir():
        raise HTTPException(404, "folder not found")
    return sorted(p.name for p in full.iterdir())


@router.get("/outputs/file")
async def outputs_file(path: str):
    full = _safe_join(path)
    if not full.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(full, filename=full.name)


# --------------------------------------------------------------------------- #
#  Live log tail
# --------------------------------------------------------------------------- #


@router.get("/logs")
async def tail_logs(site: str, tail: int = Query(200, ge=1, le=2000)):
    """Return the last *tail* lines of today’s log file for *site*."""
    log = _BASE_OUTPUT / site / "logs" / f"{pd.Timestamp.utcnow():%Y%m%d}.log"
    if not log.exists():
        raise HTTPException(404, "log not found")

    with log.open("rb") as fh:
        last = fh.readlines()[-tail:]
    return StreamingResponse(
        io.BytesIO(b"".join(last)), media_type="text/plain"
    )


# --------------------------------------------------------------------------- #
#  Pipeline control – forward simple commands to the background watcher
# --------------------------------------------------------------------------- #


@router.post("/command")
async def enqueue_command(cmd: CommandRequest):
    if cmd.stop:
        CMD_Q.put("stop")
    elif cmd.full_build:
        CMD_Q.put("full_build")
    elif cmd.run_once:
        CMD_Q.put("run_once")
    else:
        raise HTTPException(400, "no command flag set")
    return {"queued": True}
