"""Modelos de dominio simples."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class AsesoriaDetalle:
    asesor_recursos: Optional[str] = None
    nombre_asesoria: Optional[str] = None
    modalidad_programa: Optional[str] = None
    asesor_metodologico: Optional[str] = None
    fecha: Optional[date] = None


@dataclass
class RegistroFiltro:
    query: str = ""
    page_size: int = 15


@dataclass
class HistorialItem:
    numero: int
    fecha: str
    asesorias: str
    asesor_recursos: str
    asesor_metodologico: str


@dataclass
class HistorialTabla:
    items: List[HistorialItem] = field(default_factory=list)
