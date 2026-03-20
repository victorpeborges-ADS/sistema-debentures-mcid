from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class RepositoryDocument(Base):
    __tablename__ = "repository_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # parecer | portaria
    filename: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    content_mime: Mapped[str] = mapped_column(String(128), default="text/plain")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # parecer | portaria
    municipio: Mapped[str] = mapped_column(String(512), default="")
    secao: Mapped[str] = mapped_column(String(512), default="")
    avaliacao: Mapped[int] = mapped_column(Integer, default=3)
    comentario: Mapped[str] = mapped_column(Text, default="")
    autor: Mapped[str] = mapped_column(String(256), default="")
    provedor_ia: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def make_engine(url: str):
    return create_engine(url, pool_pre_ping=True, future=True)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


SessionLocal = None


def get_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False, future=True)
