"""initial smart parking schema"""
from alembic import op
import sqlalchemy as sa

revision = "20261005_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("parking_buildings",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("building_code",sa.String(20),nullable=False),sa.Column("building_name",sa.String(160),nullable=False),sa.Column("description",sa.Text()),sa.Column("is_active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("building_code"))
    op.create_table("parking_floors",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("building_id",sa.Integer(),sa.ForeignKey("parking_buildings.id"),nullable=False),sa.Column("floor_code",sa.String(20),nullable=False),sa.Column("floor_name",sa.String(100),nullable=False),sa.Column("floor_number",sa.Integer(),nullable=False),sa.Column("floor_plan_file",sa.String(255)),sa.Column("is_active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("building_id","floor_code"))
    op.create_table("parking_zones",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("floor_id",sa.Integer(),sa.ForeignKey("parking_floors.id"),nullable=False),sa.Column("zone_code",sa.String(10),nullable=False),sa.Column("zone_name",sa.String(80),nullable=False),sa.Column("display_order",sa.Integer(),nullable=False),sa.Column("is_active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("floor_id","zone_code"))
    op.create_table("roles",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("code",sa.String(30),nullable=False,unique=True),sa.Column("name",sa.String(80),nullable=False))
    op.create_table("users",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("username",sa.String(80),nullable=False,unique=True),sa.Column("display_name",sa.String(120),nullable=False),sa.Column("password_hash",sa.String(255),nullable=False),sa.Column("role_code",sa.String(30),nullable=False),sa.Column("is_active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("parking_spaces",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("building_id",sa.Integer(),sa.ForeignKey("parking_buildings.id"),nullable=False),sa.Column("floor_id",sa.Integer(),sa.ForeignKey("parking_floors.id"),nullable=False),sa.Column("zone_id",sa.Integer(),sa.ForeignKey("parking_zones.id"),nullable=False),sa.Column("space_code",sa.String(40),nullable=False),sa.Column("space_number",sa.Integer(),nullable=False),sa.Column("space_type",sa.String(30),nullable=False),sa.Column("occupancy_status",sa.String(20),nullable=False),sa.Column("operational_status",sa.String(30),nullable=False),sa.Column("x_position",sa.Float(),nullable=False),sa.Column("y_position",sa.Float(),nullable=False),sa.Column("width",sa.Float(),nullable=False),sa.Column("height",sa.Float(),nullable=False),sa.Column("rotation",sa.Float(),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("is_active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("building_id","space_code"))
    op.create_table("parking_space_events",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("parking_space_id",sa.Integer(),sa.ForeignKey("parking_spaces.id"),nullable=False),sa.Column("old_status",sa.String(30),nullable=False),sa.Column("new_status",sa.String(30),nullable=False),sa.Column("event_source",sa.String(20),nullable=False),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id")),sa.Column("sensor_id",sa.Integer()),sa.Column("event_at",sa.DateTime(timezone=True),nullable=False),sa.Column("observed_at",sa.DateTime(timezone=True)),sa.Column("note",sa.Text()))
    op.create_table("audit_logs",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id")),sa.Column("action",sa.String(80),nullable=False),sa.Column("entity_type",sa.String(80),nullable=False),sa.Column("entity_id",sa.String(80),nullable=False),sa.Column("old_data",sa.Text()),sa.Column("new_data",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    for table,column in [("parking_floors","building_id"),("parking_zones","floor_id"),("parking_spaces","building_id"),("parking_spaces","floor_id"),("parking_spaces","zone_id"),("parking_spaces","space_code"),("parking_spaces","occupancy_status"),("parking_spaces","is_active"),("parking_space_events","parking_space_id"),("parking_space_events","event_at"),("audit_logs","action"),("audit_logs","created_at")]:
        op.create_index(f"ix_{table}_{column}",table,[column])


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("parking_space_events")
    op.drop_table("parking_spaces")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("parking_zones")
    op.drop_table("parking_floors")
    op.drop_table("parking_buildings")

