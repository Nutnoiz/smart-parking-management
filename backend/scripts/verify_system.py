"""Lightweight acceptance verification for local and CI use."""
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("JWT_SECRET", "verification-only")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import dashboard_summary, perform_status_update, space_events
from app.models import ParkingSpace, User
from app.schemas import StatusUpdate
from app.seed import seed_database


def main():
    print("creating schema", flush=True)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        print("seeding", flush=True)
        seed_database(db)
        print("checking summary", flush=True)
        admin = db.scalar(select(User).where(User.username == "admin"))
        summary = dashboard_summary(db, admin)
        assert summary["total"] == 704
        assert len(summary["floors"]) == 4
        assert all(row["total"] == 176 for row in summary["floors"])
        space = db.scalar(select(ParkingSpace).order_by(ParkingSpace.id))
        next_status = "AVAILABLE" if space.occupancy_status == "OCCUPIED" else "OCCUPIED"
        print("checking transition", flush=True)
        perform_status_update(db, space.id, StatusUpdate(occupancy_status=next_status, version=space.version, note="acceptance verification"), admin)
        print("checking event", flush=True)
        assert space_events(space.id, db, admin)[0]["new_status"] == next_status
    print("acceptance verification: 704 spaces and status event passed")


if __name__ == "__main__":
    main()
