"""Funciones utilitarias compartidas entre capas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, List, Optional
import unicodedata

import pandas as pd

try:
    from ftfy import fix_text as _ftfy_fix_text
except Exception:  # pragma: no cover - ftfy es opcional en el runtime
    _ftfy_fix_text = None

_MOJIBAKE_FALLBACK_CODECS = (("latin-1", "utf-8"), ("cp1252", "utf-8"))


def _basic_mojibake_fix(text: str) -> str:
    current = text
    for source, target in _MOJIBAKE_FALLBACK_CODECS:
        for _ in range(2):
            try:
                candidate = current.encode(source).decode(target)
            except UnicodeError:
                break
            if candidate == current:
                break
            current = candidate
    return current


def fix_text_encoding(value: Any, *, strip: bool = False):
    """Intenta reparar texto con encoding corrupto (menÃº -> menú)."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if not isinstance(value, str):
        return value
    text = value.strip() if strip else value
    if not text:
        return "" if strip else ""
    if _ftfy_fix_text is not None:
        cleaned = _ftfy_fix_text(text, normalization="NFC")
    else:
        cleaned = _basic_mojibake_fix(text)
    cleaned = unicodedata.normalize("NFC", cleaned)
    return cleaned.strip() if strip else cleaned


def norm_str(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        text = fix_text_encoding(value, strip=True)
    else:
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


def clean_text_dataframe(df: pd.DataFrame, *, strip: bool = True) -> pd.DataFrame:
    """Normaliza encabezados y celdas tipo texto en un DataFrame."""
    df = df.copy()
    df.columns = [fix_text_encoding(str(col), strip=True) for col in df.columns]
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda val: fix_text_encoding(val, strip=strip) if isinstance(val, str) else val)
    return df
