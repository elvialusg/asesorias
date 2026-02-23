"""Funciones utilitarias sin dependencias de Streamlit."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, List, Optional

import pandas as pd


def norm_str(value) -> Optional[str]:
    """Convierte valores vacíos a None y elimina espacios."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_fac_name(name: str) -> str:
    """Normaliza el nombre de la facultad para guardar claves limpias."""
    if not name:
        return ""
    return "_".join(filter(None, str(name).replace(",", "").split()))


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def append_pipe(existing, item) -> str:
    """Concatena valores usando ' | ' evitando duplicados vacíos."""
    item_str = norm_str(item)
    if not item_str:
        if existing is None:
            return ""
        if isinstance(existing, float) and pd.isna(existing):
            return ""
        return str(existing).strip()

    if existing is None or (isinstance(existing, float) and pd.isna(existing)):
        parts = []
    else:
        parts = [p.strip() for p in str(existing).split(" | ") if p.strip()]

    if item_str not in parts:
        parts.append(item_str)
    return " | ".join(parts)


def split_hist(value) -> List[str]:
    """Divide un historial 'a | b | c' en lista."""
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    tokens = str(value).strip()
    if not tokens:
        return []
    return [p.strip() for p in tokens.split(" | ") if p.strip()]


def join_hist(items: Iterable[str]) -> str:
    """Une listas en el formato 'a | b | c' ignorando vacíos."""
    clean = [norm_str(item) for item in items]
    return " | ".join([c for c in clean if c])


def ensure_date(value) -> Optional[date]:
    """Normaliza fechas provenientes de pandas/strings."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        ts = pd.to_datetime(value)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return ts.date()
