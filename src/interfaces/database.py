# interfaces/sqlite.py
# SQLite interface for hotkey <-> worker mapping using SQLAlchemy

from datetime import datetime
import os
from sqlalchemy import (
    DateTime,
    Float,
    create_engine,
    String,
    Column,
    BigInteger,
)
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
    registration_time_int: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    signature: Mapped[str] = mapped_column(String, nullable=False)
    unbind_signature: Mapped[Optional[str]] = mapped_column(String, nullable=True)


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
        for row in self.session.query(HotkeyWorker).filter(HotkeyWorker.unbind_signature.is_(None)).all():
            result[row.worker] = row.hotkey
        return result


class DatabaseService:
    def __init__(self, db_url: str = DATABASE_URL, max_workers: int = 30):
        self.engine = create_engine(
            db_url, connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.session = self.SessionLocal()
        self.max_workers = max_workers

    async def add_mapping(
        self,
        hotkey: str,
        worker: str,
        signature: str,
        registration_time: float | int,
    ) -> None:
        # Only add mapping to database
        existing = (
            self.session.query(HotkeyWorker).filter_by(worker=worker).first()
        )
        if existing:
            raise ValueError("Worker already registered")
        # Restrict number of workers per hotkey
        worker_count = (
            self.session.query(HotkeyWorker).filter_by(hotkey=hotkey, unbind_signature=None).count()
        )
        if worker_count >= self.max_workers:
            raise ValueError(
                f"Maximum number of workers ({self.max_workers}) for this hotkey reached"
            )
        # Store both float and int
        if isinstance(registration_time, float):
            reg_time_float = registration_time
            reg_time_int = int(registration_time * 1_000_000)
        else:
            reg_time_float = float(registration_time) / 1_000_000
            reg_time_int = int(registration_time)
        new_mapping = HotkeyWorker(
            worker=worker,
            hotkey=hotkey,
            signature=signature,
            registration_time=reg_time_float,
            registration_time_int=reg_time_int,
        )
        self.session.add(new_mapping)
        self.session.commit()
        return None  # Success

    async def get_hotkey_workers_by_time(
        self,
        since_timestamp: float = 0.0,
        page_size: int = 100,
        page_number: int = 1,
    ) -> list[dict]:
        # Convert since_timestamp to integer microseconds for comparison
        since_ts_int = int(since_timestamp * 1_000_000)
        query = (
            self.session.query(HotkeyWorker)
            .filter(HotkeyWorker.registration_time_int > since_ts_int)
            .order_by(HotkeyWorker.registration_time_int)
        )
        total = query.count()
        results = (
            query.offset((page_number - 1) * page_size).limit(page_size).all()
        )
        return [
            {
                "worker": row.worker,
                "hotkey": row.hotkey,
                "registration_time": row.registration_time,  # API compatibility
                "registration_time_int": row.registration_time_int,  # For reference
                "signature": row.signature,
            }
            for row in results
        ]

    async def mark_worker_unbound(
        self,
        hotkey: str,
        worker: str,
        unbind_signature: str,
    ) -> None:
        # Mark the worker as unbound by setting unbind_signature
        obj = self.session.query(HotkeyWorker).filter_by(hotkey=hotkey, worker=worker).first()
        if not obj:
            raise ValueError("Worker not found for this hotkey")
        if obj.unbind_signature:
            raise ValueError("Worker already unbound")
        obj.unbind_signature = unbind_signature
        self.session.commit()
        return None


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
