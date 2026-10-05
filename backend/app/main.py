import json
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from .auth import create_token, current_user, decode_token, require_update, verify_password
from .database import Base, SessionLocal, engine, get_db
from .models import AuditLog, ParkingFloor, ParkingSpace, ParkingSpaceEvent, ParkingZone, User
from .schemas import FloorOut, LayoutUpdate, LoginRequest, SpaceOut, StatusUpdate, TokenResponse
from .seed import seed_database


class ConnectionManager:
    def __init__(self):
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict):
        stale = []
        for connection in self.connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield


app = FastAPI(title="Smart Parking Management API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def effective_status(space: ParkingSpace) -> str:
    return "DISABLED" if space.operational_status == "OUT_OF_SERVICE" else space.occupancy_status


def summary_rows(db: Session):
    rows = db.execute(
        select(
            ParkingFloor.id,
            ParkingFloor.floor_code,
            ParkingFloor.floor_name,
            ParkingFloor.floor_number,
            func.count(ParkingSpace.id).label("total"),
            func.sum(case((ParkingSpace.operational_status == "OUT_OF_SERVICE", 1), else_=0)).label("disabled"),
            func.sum(case(((ParkingSpace.operational_status == "ACTIVE") & (ParkingSpace.occupancy_status == "AVAILABLE"), 1), else_=0)).label("available"),
            func.sum(case(((ParkingSpace.operational_status == "ACTIVE") & (ParkingSpace.occupancy_status == "OCCUPIED"), 1), else_=0)).label("occupied"),
        )
        .join(ParkingSpace, ParkingSpace.floor_id == ParkingFloor.id)
        .where(ParkingFloor.is_active.is_(True), ParkingSpace.is_active.is_(True))
        .group_by(ParkingFloor.id)
        .order_by(ParkingFloor.floor_number)
    ).all()
    result = []
    for row in rows:
        total, available, occupied, disabled = int(row.total), int(row.available or 0), int(row.occupied or 0), int(row.disabled or 0)
        active_capacity = max(1, total - disabled)
        result.append(
            FloorOut(
                id=row.id,
                floor_code=row.floor_code,
                floor_name=row.floor_name,
                floor_number=row.floor_number,
                total=total,
                available=available,
                occupied=occupied,
                disabled=disabled,
                occupancy_rate=round(occupied / active_capacity * 100, 1),
            )
        )
    return result


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username, User.is_active.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return TokenResponse(access_token=create_token(user), display_name=user.display_name, role=user.role_code)


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role_code}


@app.get("/api/floors", response_model=list[FloorOut])
def floors(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return summary_rows(db)


@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), _: User = Depends(current_user)):
    floors_data = summary_rows(db)
    total = sum(row.total for row in floors_data)
    available = sum(row.available for row in floors_data)
    occupied = sum(row.occupied for row in floors_data)
    disabled = sum(row.disabled for row in floors_data)
    active_capacity = max(1, total - disabled)
    return {
        "building_code": "PA",
        "building_name": "Parking Building A",
        "total": total,
        "available": available,
        "occupied": occupied,
        "disabled": disabled,
        "occupancy_rate": round(occupied / active_capacity * 100, 1),
        "floors": [row.model_dump() for row in floors_data],
    }


@app.get("/api/floors/{floor_id}/map")
def floor_map(floor_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    floor = db.get(ParkingFloor, floor_id)
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")
    zones = db.scalars(select(ParkingZone).where(ParkingZone.floor_id == floor_id).order_by(ParkingZone.display_order)).all()
    spaces = db.scalars(select(ParkingSpace).where(ParkingSpace.floor_id == floor_id, ParkingSpace.is_active.is_(True)).order_by(ParkingSpace.space_code)).all()
    by_zone: dict[int, list[dict]] = defaultdict(list)
    for space in spaces:
        item = SpaceOut.model_validate(space).model_dump()
        item["effective_status"] = effective_status(space)
        by_zone[space.zone_id].append(item)
    return {
        "id": floor.id,
        "floor_code": floor.floor_code,
        "floor_name": floor.floor_name,
        "view_box": "0 0 1740 700",
        "zones": [{"id": zone.id, "zone_code": zone.zone_code, "zone_name": zone.zone_name, "spaces": by_zone[zone.id]} for zone in zones],
    }


@app.get("/api/parking/available")
def available_spaces(
    floor_id: int | None = None,
    zone: str | None = None,
    space_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    query = select(ParkingSpace).join(ParkingZone).where(
        ParkingSpace.is_active.is_(True),
        ParkingSpace.operational_status == "ACTIVE",
        ParkingSpace.occupancy_status == "AVAILABLE",
    )
    if floor_id:
        query = query.where(ParkingSpace.floor_id == floor_id)
    if zone:
        query = query.where(ParkingZone.zone_code == zone.upper())
    if space_type:
        query = query.where(ParkingSpace.space_type == space_type.upper())
    return [SpaceOut.model_validate(space) for space in db.scalars(query.order_by(ParkingSpace.space_code).limit(limit)).all()]


def perform_status_update(db: Session, space_id: int, payload: StatusUpdate, user: User):
    space = db.scalar(select(ParkingSpace).where(ParkingSpace.id == space_id).with_for_update())
    if not space:
        raise HTTPException(status_code=404, detail="Parking space not found")
    if space.version != payload.version:
        raise HTTPException(status_code=409, detail="Space was updated by another operator")
    old_effective = effective_status(space)
    old_data = {"occupancy_status": space.occupancy_status, "operational_status": space.operational_status, "version": space.version}
    if payload.occupancy_status is not None:
        space.occupancy_status = payload.occupancy_status
    if payload.operational_status is not None:
        space.operational_status = payload.operational_status
    new_effective = effective_status(space)
    if old_effective == new_effective and old_data["occupancy_status"] == space.occupancy_status and old_data["operational_status"] == space.operational_status:
        return {**SpaceOut.model_validate(space).model_dump(), "effective_status": new_effective}
    space.version += 1
    event = ParkingSpaceEvent(
        parking_space_id=space.id,
        old_status=old_effective,
        new_status=new_effective,
        event_source="MANUAL",
        user_id=user.id,
        note=payload.note,
    )
    db.add(event)
    db.add(
        AuditLog(
            user_id=user.id,
            action="PARKING_STATUS_CHANGED",
            entity_type="parking_space",
            entity_id=str(space.id),
            old_data=json.dumps(old_data),
            new_data=json.dumps({"occupancy_status": space.occupancy_status, "operational_status": space.operational_status, "version": space.version}),
        )
    )
    db.commit()
    db.refresh(space)
    return {**SpaceOut.model_validate(space).model_dump(), "effective_status": effective_status(space)}


@app.post("/api/spaces/{space_id}/status")
async def update_status(
    space_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_update),
):
    result = perform_status_update(db, space_id, payload, user)
    await manager.broadcast({"type": "parking_space_status_changed", "space": result})
    return result


@app.put("/api/floors/{floor_id}/layout")
def update_layout(
    floor_id: int,
    payload: LayoutUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_update),
):
    updated = 0
    for item in payload.spaces:
        space = db.scalar(select(ParkingSpace).where(ParkingSpace.id == item.id, ParkingSpace.floor_id == floor_id).with_for_update())
        if not space:
            raise HTTPException(status_code=404, detail=f"Space {item.id} not found")
        if space.version != item.version:
            raise HTTPException(status_code=409, detail=f"Space {space.space_code} changed")
        space.x_position, space.y_position = item.x_position, item.y_position
        space.width, space.height, space.rotation = item.width, item.height, item.rotation
        space.version += 1
        updated += 1
    db.add(AuditLog(user_id=user.id, action="FLOOR_LAYOUT_CHANGED", entity_type="parking_floor", entity_id=str(floor_id), new_data=json.dumps({"updated_spaces": updated})))
    db.commit()
    return {"updated": updated}


@app.get("/api/spaces/{space_id}/events")
def space_events(space_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    events = db.scalars(select(ParkingSpaceEvent).where(ParkingSpaceEvent.parking_space_id == space_id).order_by(ParkingSpaceEvent.event_at.desc()).limit(100)).all()
    return [{"id": e.id, "old_status": e.old_status, "new_status": e.new_status, "event_source": e.event_source, "event_at": e.event_at, "note": e.note} for e in events]


@app.get("/api/events")
def recent_events(limit: int = Query(default=25, ge=1, le=200), db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = db.execute(select(ParkingSpaceEvent, ParkingSpace.space_code).join(ParkingSpace).order_by(ParkingSpaceEvent.event_at.desc()).limit(limit)).all()
    return [{"id": event.id, "space_code": code, "old_status": event.old_status, "new_status": event.new_status, "event_source": event.event_source, "event_at": event.event_at, "note": event.note} for event, code in rows]


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")):
    try:
        decode_token(token)
    except HTTPException:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
