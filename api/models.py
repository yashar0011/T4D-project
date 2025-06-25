from pydantic import BaseModel, Field
from typing    import Optional


class SettingsRow(BaseModel):
    id:                 int
    Site:               str
    PointName:          str
    SensorID:           int
    Type:               Literal["Reflective", "Reflectless"]
    CSVImport:          bool
    SQLImport:          bool | None = None
    SQLSensorID:        int  | None = None
    TimeStampOffset:    float | None = None
    TerrestrialFileName:   str | None = None
    TerrestrialPointName:  str | None = None
    TerrestrialColumnName: str | None = None


class SettingsUpdate(BaseModel):
    field: str
    value: str | int | float | bool


class DeltaPoint(BaseModel):
    TIMESTAMP: str      # ISO UTC
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