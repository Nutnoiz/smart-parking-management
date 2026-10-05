import os
import secrets

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["INITIAL_ADMIN_PASSWORD"] = secrets.token_urlsafe(24)

import pytest
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User
from app.seed import seed_database


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def admin(db):
    return db.scalar(select(User).where(User.username == "admin"))
