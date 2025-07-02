from pydantic import BaseModel, Field
from typing    import Optional, Literal


class SettingsRow(BaseModel):
    id:                int
    Site:              str
    PointName:         str
    Type:              Literal["Reflective", "Reflectless"]

    # ingestion / export flags
    CSVImport:         bool
    SQLImport:         bool | None = None
    SQLSensorID:       int  | None = None

    # terrestrial links
    TimeStampOffset:        float | None = None      # minutes  (+ east, – west)
    TerrestrialFileName:    str   | None = None
    TerrestrialPointName:   str   | None = None
    TerrestrialColumnName:  str   | None = None

    # instrument baselines
    BaselineN:         float | None = None
    BaselineE:         float | None = None
    BaselineH:         float

    StartUTC:          str = Field(..., description="ISO UTC as text")


class SettingsUpdate(BaseModel):
    field: str
    value: str | int | float | bool


class DeltaPoint(BaseModel):
    TIMESTAMP: str
    Delta_H_mm: float
    Delta_N_mm: Optional[float] = None
    Delta_E_mm: Optional[float] = None


class DeltasResponse(BaseModel):
    point: str
    rows:  list[DeltaPoint]


class CommandRequest(BaseModel):
    stop:       bool = False
    full_build: bool = False
    run_once:   bool = False