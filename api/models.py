from typing import Literal, Optional
from pydantic import BaseModel, Field


class SettingsRow(BaseModel):
    # ── spreadsheet columns ───────────────────────────────
    id:         int                       # injected by /routes.py
    Site:       str
    PointName:  str
    Type:       Literal["Reflective", "Reflectless"]

    CSVImport:  bool
    SQLImport:  Optional[bool] = None
    SQLSensorID: Optional[int] = None

    FileProfile: str                      # ← NEW (links to FileProfiles sheet)
    TerrestrialPointName: Optional[str] = None

    BaselineN: Optional[float] = None
    BaselineE: Optional[float] = None
    BaselineH: float                     # mandatory for ΔH

    StartUTC: str = Field(..., description="ISO 8601 UTC")

    # pydantic config (optional strictness)
    model_config = {"extra": "ignore"}    # ignore accidental extra cols


class SettingsUpdate(BaseModel):
    field: str
    value: str | int | float | bool


class DeltaPoint(BaseModel):
    TIMESTAMP: str            # ISO-8601 UTC
    Delta_H_mm: float
    Delta_N_mm: Optional[float] = None
    Delta_E_mm: Optional[float] = None


class DeltasResponse(BaseModel):
    point: str
    rows: list[DeltaPoint]


class CommandRequest(BaseModel):
    stop:       bool = False
    full_build: bool = False
    run_once:   bool = False