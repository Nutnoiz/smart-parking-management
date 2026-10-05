"""Place the ramps inline between zones A, B, and C on existing plans."""

from alembic import op
import sqlalchemy as sa

revision = "20261005_03"
down_revision = "20261005_02"
branch_labels = None
depends_on = None


def geometry(zone: str, number: int, *, previous: bool):
    if zone in {"D", "E"}:
        start, gap = (50, 31) if previous else (55, 34)
        return start + (number - 1) * gap, 64 if zone == "D" else 604, 24, 32

    config = (
        {"A": (100, 260, 10, 32), "B": (510, 260, 20, 29), "C": (1240, 260, 10, 29)}
        if previous
        else {"A": (70, 260, 10, 30), "B": (570, 260, 20, 28), "C": (1340, 260, 10, 30)}
    )
    start_x, start_y, per_row, gap = config[zone]
    row = 0 if number <= per_row else 1
    col = (number - 1) % per_row
    return start_x + col * gap, start_y + row * 98, 23, 54


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT ps.id, pz.zone_code, ps.space_number, ps.x_position, ps.y_position, ps.width, ps.height "
        "FROM parking_spaces ps JOIN parking_zones pz ON pz.id = ps.zone_id"
    )).mappings()
    for row in rows:
        previous = geometry(row["zone_code"], row["space_number"], previous=True)
        current = tuple(float(row[key]) for key in ("x_position", "y_position", "width", "height"))
        if any(abs(actual - expected) > 0.001 for actual, expected in zip(current, previous)):
            continue  # Preserve spaces that an operator has already positioned manually.
        x, y, width, height = geometry(row["zone_code"], row["space_number"], previous=False)
        connection.execute(sa.text(
            "UPDATE parking_spaces SET x_position=:x, y_position=:y, width=:w, height=:h, version=version+1 WHERE id=:id"
        ), {"x": x, "y": y, "w": width, "h": height, "id": row["id"]})


def downgrade():
    pass
