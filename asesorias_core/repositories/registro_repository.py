"""Repositorio para manejar los registros de asesorías."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import RegistroAsesoria


class RegistroRepository:
    """Encapsula las operaciones CRUD contra la tabla registros_asesorias."""

    def _match_by_cedula(self, session: Session, cedula: str) -> Optional[RegistroAsesoria]:
        if not cedula:
            return None
        stmt = select(RegistroAsesoria).where(RegistroAsesoria.cedula == cedula).limit(1)
        return session.scalar(stmt)

    def _match_by_nombre(self, session: Session, nombre: str) -> Optional[RegistroAsesoria]:
        if not nombre:
            return None
        stmt = select(RegistroAsesoria).where(func.lower(RegistroAsesoria.nombre_usuario) == nombre.lower()).limit(1)
        return session.scalar(stmt)

    # Lecturas ---------------------------------------------------------------
    def list_all(self) -> list[RegistroAsesoria]:
        with get_session() as session:
            stmt = select(RegistroAsesoria).order_by(RegistroAsesoria.id.asc())
            return list(session.scalars(stmt))

    def get_by_id(self, record_id: int) -> Optional[RegistroAsesoria]:
        with get_session() as session:
            return session.get(RegistroAsesoria, record_id)

    def get_by_identifiers(self, cedula: Optional[str], nombre: Optional[str]) -> Optional[RegistroAsesoria]:
        with get_session() as session:
            match = self._match_by_cedula(session, cedula or "")
            if match:
                return match
            return self._match_by_nombre(session, nombre or "")

    # Escrituras -------------------------------------------------------------
    def create(self, data: Dict) -> RegistroAsesoria:
        new_record = RegistroAsesoria(**data)
        with get_session() as session:
            session.add(new_record)
            session.flush()
            session.refresh(new_record)
            return new_record

    def update(self, record_id: int, data: Dict) -> Optional[RegistroAsesoria]:
        with get_session() as session:
            record = session.get(RegistroAsesoria, record_id)
            if record is None:
                return None
            for field, value in data.items():
                setattr(record, field, value)
            session.flush()
            session.refresh(record)
            return record

    def delete(self, record_id: int) -> bool:
        with get_session() as session:
            record = session.get(RegistroAsesoria, record_id)
            if record is None:
                return False
            session.delete(record)
            return True

    def bulk_upsert(self, rows: Iterable[Dict], key_fields=("cedula", "nombre_usuario")) -> None:
        """Importación sencilla: si coincide por cédula o nombre, se actualiza; de lo contrario se crea."""
        with get_session() as session:
            for row in rows:
                match = None
                ced = row.get(key_fields[0])
                nom = row.get(key_fields[1])
                if ced:
                    match = self._match_by_cedula(session, ced)
                if match is None and nom:
                    match = self._match_by_nombre(session, nom)

                if match:
                    for field, value in row.items():
                        setattr(match, field, value)
                else:
                    session.add(RegistroAsesoria(**row))
