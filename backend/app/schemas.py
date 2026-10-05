from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    display_name: str
    role: str


class StatusUpdate(BaseModel):
    occupancy_status: Literal["AVAILABLE", "OCCUPIED", "UNKNOWN"] | None = None
    operational_status: Literal["ACTIVE", "OUT_OF_SERVICE"] | None = None
    version: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=500)


class LayoutItem(BaseModel):
    id: int
    x_position: float
    y_position: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: float = 0
    version: int = Field(ge=1)


class LayoutUpdate(BaseModel):
    spaces: list[LayoutItem]


class SpaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    space_code: str
    space_number: int
    space_type: str
    occupancy_status: str
    operational_status: str
    x_position: float
    y_position: float
    width: float
    height: float
    rotation: float
    version: int
    is_active: bool
    updated_at: datetime


class FloorOut(BaseModel):
    id: int
    floor_code: str
    floor_name: str
    floor_number: int
    total: int
    available: int
    occupied: int
    disabled: int
    occupancy_rate: float

