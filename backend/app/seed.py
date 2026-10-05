import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import ParkingBuilding, ParkingFloor, ParkingSpace, ParkingZone, Role, User


ZONE_COUNTS = {"A": 20, "B": 40, "C": 20, "D": 48, "E": 48}


def _slot_geometry(zone: str, number: int) -> tuple[float, float, float, float, float]:
    """Coordinates use a 1740 x 700 plan with ramps after zones A and B."""
    if zone in {"D", "E"}:
        return 55 + (number - 1) * 34, 64 if zone == "D" else 604, 24, 32, 0

    config = {
        "A": (70, 260, 10, 30),
        "B": (570, 260, 20, 28),
        "C": (1340, 260, 10, 30),
    }
    start_x, start_y, per_row, gap = config[zone]
    row = 0 if number <= per_row else 1
    col = (number - 1) % per_row
    return start_x + col * gap, start_y + row * 98, 23, 54, 0


def seed_database(db: Session) -> None:
    if db.scalar(select(func.count(ParkingBuilding.id))):
        return

    initial_admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "").strip()
    if not initial_admin_password:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must be set before initializing a new database")

    for code, name in [
        ("ADMIN", "Administrator"),
        ("PARKING_MANAGER", "Parking Manager"),
        ("OPERATOR", "Operator"),
        ("VIEWER", "Viewer"),
    ]:
        db.add(Role(code=code, name=name))

    admin = User(
        username="admin",
        display_name="System Administrator",
        password_hash=hash_password(initial_admin_password),
        role_code="ADMIN",
    )
    db.add(admin)
    building = ParkingBuilding(building_code="PA", building_name="Parking Building A")
    db.add(building)
    db.flush()

    global_index = 0
    for floor_number in range(1, 5):
        floor = ParkingFloor(
            building_id=building.id,
            floor_code=f"F{floor_number}",
            floor_name=f"Floor {floor_number}",
            floor_number=floor_number,
            floor_plan_file="logical-floor-plan-v1.svg",
        )
        db.add(floor)
        db.flush()
        for order, (zone_code, count) in enumerate(ZONE_COUNTS.items(), start=1):
            zone = ParkingZone(
                floor_id=floor.id,
                zone_code=zone_code,
                zone_name=f"Zone {zone_code}",
                display_order=order,
            )
            db.add(zone)
            db.flush()
            for number in range(1, count + 1):
                global_index += 1
                occupancy = "OCCUPIED" if global_index % 5 in {0, 1} else "AVAILABLE"
                operational = "OUT_OF_SERVICE" if global_index % 89 == 0 else "ACTIVE"
                x, y, width, height, rotation = _slot_geometry(zone_code, number)
                db.add(
                    ParkingSpace(
                        building_id=building.id,
                        floor_id=floor.id,
                        zone_id=zone.id,
                        space_code=f"F{floor_number}-{zone_code}{number:02d}",
                        space_number=number,
                        occupancy_status=occupancy,
                        operational_status=operational,
                        x_position=x,
                        y_position=y,
                        width=width,
                        height=height,
                        rotation=rotation,
                    )
                )
    db.commit()
