from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ParkingBuilding(TimestampMixin, Base):
    __tablename__ = "parking_buildings"
    id: Mapped[int] = mapped_column(primary_key=True)
    building_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    building_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    floors: Mapped[list["ParkingFloor"]] = relationship(back_populates="building", cascade="all, delete-orphan")


class ParkingFloor(TimestampMixin, Base):
    __tablename__ = "parking_floors"
    __table_args__ = (UniqueConstraint("building_id", "floor_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("parking_buildings.id"), index=True)
    floor_code: Mapped[str] = mapped_column(String(20))
    floor_name: Mapped[str] = mapped_column(String(100))
    floor_number: Mapped[int] = mapped_column(Integer)
    floor_plan_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    building: Mapped[ParkingBuilding] = relationship(back_populates="floors")
    zones: Mapped[list["ParkingZone"]] = relationship(back_populates="floor", cascade="all, delete-orphan")


class ParkingZone(TimestampMixin, Base):
    __tablename__ = "parking_zones"
    __table_args__ = (UniqueConstraint("floor_id", "zone_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("parking_floors.id"), index=True)
    zone_code: Mapped[str] = mapped_column(String(10))
    zone_name: Mapped[str] = mapped_column(String(80))
    display_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    floor: Mapped[ParkingFloor] = relationship(back_populates="zones")
    spaces: Mapped[list["ParkingSpace"]] = relationship(back_populates="zone", cascade="all, delete-orphan")


class ParkingSpace(TimestampMixin, Base):
    __tablename__ = "parking_spaces"
    __table_args__ = (UniqueConstraint("building_id", "space_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("parking_buildings.id"), index=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("parking_floors.id"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("parking_zones.id"), index=True)
    space_code: Mapped[str] = mapped_column(String(40), index=True)
    space_number: Mapped[int] = mapped_column(Integer)
    space_type: Mapped[str] = mapped_column(String(30), default="STANDARD")
    occupancy_status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", index=True)
    operational_status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    x_position: Mapped[float] = mapped_column(Float)
    y_position: Mapped[float] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float, default=18)
    height: Mapped[float] = mapped_column(Float, default=34)
    rotation: Mapped[float] = mapped_column(Float, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    zone: Mapped[ParkingZone] = relationship(back_populates="spaces")
    events: Mapped[list["ParkingSpaceEvent"]] = relationship(back_populates="parking_space", cascade="all, delete-orphan")


class ParkingSpaceEvent(Base):
    __tablename__ = "parking_space_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    parking_space_id: Mapped[int] = mapped_column(ForeignKey("parking_spaces.id"), index=True)
    old_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    event_source: Mapped[str] = mapped_column(String(20), default="MANUAL")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sensor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    parking_space: Mapped[ParkingSpace] = relationship(back_populates="events")


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(80))


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_code: Mapped[str] = mapped_column(String(30), default="VIEWER")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    old_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

