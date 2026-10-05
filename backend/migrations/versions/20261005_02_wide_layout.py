"""widen logical floor plan to prevent overlapping slots"""
from alembic import op
import sqlalchemy as sa

revision = "20261005_02"
down_revision = "20261005_01"
branch_labels = None
depends_on = None


def geometry(zone: str, number: int):
    if zone in {"D", "E"}:
        return 55 + (number - 1) * 34, 64 if zone == "D" else 604, 24, 32
    start_x, start_y, per_row, gap = {
        "A": (70, 260, 10, 30),
        "B": (570, 260, 20, 28),
        "C": (1340, 260, 10, 30),
    }[zone]
    row = 0 if number <= per_row else 1
    col = (number - 1) % per_row
    return start_x + col * gap, start_y + row * 98, 23, 54


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT ps.id, pz.zone_code, ps.space_number FROM parking_spaces ps JOIN parking_zones pz ON pz.id = ps.zone_id")).mappings()
    for row in rows:
        x, y, width, height = geometry(row["zone_code"], row["space_number"])
        connection.execute(sa.text("UPDATE parking_spaces SET x_position=:x, y_position=:y, width=:w, height=:h, version=version+1 WHERE id=:id"), {"x": x, "y": y, "w": width, "h": height, "id": row["id"]})


def downgrade():
    pass
