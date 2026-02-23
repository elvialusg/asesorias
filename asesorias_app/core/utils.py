"""Funciones utilitarias compartidas entre capas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, List, Optional

import pandas as pd


def norm_str(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_fac_name(name: str) -> str:
    if not name:
        return ""
    cleaned = str(name).strip().replace(",", "")
    return "_".join([p for p in cleaned.split() if p])


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def append_pipe(existing, item) -> str:
    item_text = norm_str(item)
    if not item_text:
        if existing is None:
            return ""
        if isinstance(existing, float) and pd.isna(existing):
            return ""
        return str(existing).strip()

    if existing is None or (isinstance(existing, float) and pd.isna(existing)):
        parts: List[str] = []
    else:
        parts = [p.strip() for p in str(existing).split(" | ") if p.strip()]

    if item_text not in parts:
        parts.append(item_text)
    return " | ".join(parts)


def split_hist(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    return [p.strip() for p in text.split(" | ") if p.strip()]


def join_hist(items: Iterable[str]) -> str:
    cleaned = [norm_str(item) for item in items]
    return " | ".join([c for c in cleaned if c])


def ensure_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        dt = pd.to_datetime(value, errors="coerce")
    except Exception:
        return None
    if pd.isna(dt):
        return None
    return dt.date()
