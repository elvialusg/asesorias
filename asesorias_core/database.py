"""Configuración de SQLAlchemy y helpers de sesión."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Crea las tablas necesarias si aún no existen."""
    from .models import Base  # Import diferido para evitar ciclos

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Session:
    """Context manager conveniente para obtener una sesión."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
