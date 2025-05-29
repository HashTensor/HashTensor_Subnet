# interfaces/sqlite.py
# SQLite interface for hotkey <-> worker mapping using SQLAlchemy

from datetime import datetime
import os
from sqlalchemy import DateTime, create_engine, String
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    Mapped,
    mapped_column,
)
from ..mapping import MappingSource
from typing import Optional

DATABASE_URL = f"sqlite:///data/mapping.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class HotkeyWorker(Base):
    __tablename__ = "hotkey_worker"
    worker: Mapped[str] = mapped_column(String, primary_key=True)
    hotkey: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    signature: Mapped[str] = mapped_column(String, nullable=False)


class SqliteMappingSource(MappingSource):
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(
            db_url, connect_args={"check_same_thread": False}
        )
        self.session = SessionLocal()

    async def load_mapping(self):
        # Load mapping from SQLite database: worker -> hotkey
        # This is a synchronous DB call, but the method is async for interface compatibility
        result = {}
        for row in self.session.query(HotkeyWorker).all():
            result[row.worker] = row.hotkey
        return result


class DatabaseService:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(
            db_url, connect_args={"check_same_thread": False}
        )
        self.session = SessionLocal()

    async def add_mapping(
        self, hotkey: str, worker: str, signature: str
    ) -> None:
        # Only add mapping to database
        existing = (
            self.session.query(HotkeyWorker).filter_by(worker=worker).first()
        )
        if existing:
            raise ValueError("Worker already registered")
        new_mapping = HotkeyWorker(
            worker=worker, hotkey=hotkey, signature=signature
        )
        self.session.add(new_mapping)
        self.session.commit()
        return None  # Success
