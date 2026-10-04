"""SQLite via SQLAlchemy 2 (§5.6). Tables are created at startup with create_all (no Alembic)."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import DB_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    if DB_URL.startswith("sqlite"):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session():
    with SessionLocal() as s:
        yield s
