# interfaces/sqlite.py
# SQLite interface for hotkey <-> worker mapping using SQLAlchemy

from datetime import datetime
import os
from sqlalchemy import DateTime, Float, create_engine, String, Column
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    Mapped,
    mapped_column,
)
from ..mapping import MappingSource
from typing import Optional

DATABASE_URL = f"sqlite:///data/mapping.db"

Base = declarative_base()


class HotkeyWorker(Base):
    __tablename__ = "hotkey_worker"
    worker: Mapped[str] = mapped_column(String, primary_key=True)
    hotkey: Mapped[str] = mapped_column(String, nullable=False)
    registration_time: Mapped[float] = mapped_column(Float, nullable=False)
    signature: Mapped[str] = mapped_column(String, nullable=False)


class SqliteMappingSource(MappingSource):
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(
            db_url, connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.session = self.SessionLocal()

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
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.session = self.SessionLocal()

    async def add_mapping(
        self,
        hotkey: str,
        worker: str,
        signature: str,
        registration_time: float,
    ) -> None:
        # Only add mapping to database
        existing = (
            self.session.query(HotkeyWorker).filter_by(worker=worker).first()
        )
        if existing:
            raise ValueError("Worker already registered")
        new_mapping = HotkeyWorker(
            worker=worker,
            hotkey=hotkey,
            signature=signature,
            registration_time=registration_time,
        )
        self.session.add(new_mapping)
        self.session.commit()
        return None  # Success


class DynamicConfig(Base):
    __tablename__ = "dynamic_config"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)


class DynamicConfigService:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(
            db_url, connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.session = self.SessionLocal()

    def _get(self, key: str, default=None):
        row = self.session.query(DynamicConfig).filter_by(key=key).first()
        if row:
            return row.value
        return default

    def _set(self, key: str, value: str):
        row = self.session.query(DynamicConfig).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            row = DynamicConfig(key=key, value=value)
            self.session.add(row)
        self.session.commit()

    def get_last_set_weights_time(self) -> float:
        value = self._get("last_set_weights_time")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def set_last_set_weights_time(self, timestamp: float):
        self._set("last_set_weights_time", str(timestamp))
