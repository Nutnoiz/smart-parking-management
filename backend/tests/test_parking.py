import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.main import dashboard_summary, perform_status_update, space_events
from app.models import ParkingFloor, ParkingSpace
from app.schemas import StatusUpdate


def test_seed_counts(db, admin):
    data = dashboard_summary(db, admin)
    assert data["total"] == 704
    assert len(data["floors"]) == 4
    assert all(floor["total"] == 176 for floor in data["floors"])


def test_status_transition_creates_event(db, admin):
    floor = db.scalar(select(ParkingFloor).order_by(ParkingFloor.floor_number))
    space = db.scalar(select(ParkingSpace).where(ParkingSpace.floor_id == floor.id).order_by(ParkingSpace.id))
    new_status = "OCCUPIED" if space.occupancy_status == "AVAILABLE" else "AVAILABLE"
    result = perform_status_update(db, space.id, StatusUpdate(occupancy_status=new_status, version=space.version, note="automated test"), admin)
    assert result["occupancy_status"] == new_status
    events = space_events(space.id, db, admin)
    assert events[0]["event_source"] == "MANUAL"
    assert events[0]["note"] == "automated test"


def test_rejects_stale_version(db, admin):
    space = db.scalar(select(ParkingSpace).order_by(ParkingSpace.id))
    with pytest.raises(HTTPException) as error:
        perform_status_update(db, space.id, StatusUpdate(occupancy_status="AVAILABLE", version=space.version + 9), admin)
    assert error.value.status_code == 409
