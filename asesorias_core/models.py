"""Modelos ORM usados en la capa de repositorios."""

from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RegistroAsesoria(Base):
    """Representa una fila del registro consolidado."""

    __tablename__ = "registros_asesorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre_facultad = Column(String(255), nullable=False, default="")
    nombre_programa = Column(String(255), nullable=False, default="")
    cedula = Column(String(64), nullable=True, index=True)
    nombre_usuario = Column(String(255), nullable=True, index=True)
    asesor_recursos_academicos = Column(String(255), nullable=True)
    nombre_asesoria = Column(String(255), nullable=True)
    modalidad = Column(String(128), nullable=True)
    asesor_metodologico_detalle = Column(String(255), nullable=True)
    titulo_trabajo_grado = Column(String(255), nullable=True)
    fecha = Column(Date, nullable=True)
    revision_inicial = Column(String(128), nullable=True)
    revision_plantilla = Column(String(128), nullable=True)
    ok_referencistas = Column(String(128), nullable=True)
    ok_servicios = Column(String(128), nullable=True)
    observaciones = Column(Text, nullable=True)
    escaneado_turnitin = Column(String(128), nullable=True)
    porcentaje_similitud = Column(Float, nullable=True)
    aprobacion_similitud = Column(String(128), nullable=True)
    modalidad_programa = Column(String(128), nullable=True)
    total_asesorias = Column(Integer, nullable=False, default=0)
    historial_asesorias = Column(Text, nullable=True)
    historial_asesor_recursos = Column(Text, nullable=True)
    historial_asesor_metodologico = Column(Text, nullable=True)
    historial_fechas = Column(Text, nullable=True)
    paz_y_salvo = Column(String(128), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - solo debug
        return f"<RegistroAsesoria id={self.id} cedula={self.cedula!r} nombre={self.nombre_usuario!r}>"
