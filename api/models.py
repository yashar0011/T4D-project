from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class DeltaRow(BaseModel):
    TIMESTAMP: datetime
    SensorID:  int
    PointName: str
    Delta_H_mm: float
    Delta_N_mm: Optional[float] = None
    Delta_E_mm: Optional[float] = None

class DeltasResponse(BaseModel):
    point: str
    rows: List[DeltaRow]

class SettingsRow(BaseModel):
    id: int  # index in Settings.xlsx
    Active: bool
    SensorID: int
    Site: str
    PointName: str
    Type: str
    ImportFolder: str
    ExportFolder: str
    BaselineN: Optional[float]
    BaselineE: Optional[float]
    BaselineH: float
    OutlierMAD: float
    StartUTC: datetime

class SettingsUpdate(BaseModel):
    field: str
    value: str | float | bool

class CommandRequest(BaseModel):
    run_once: bool = False
    full_build: bool = False
    stop: bool = False