"""Configuración simple basada en variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


@dataclass
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/asesorias",
    )
    template_path: str = os.getenv(
        "ASESORIAS_TEMPLATE_PATH",
        str(DATA_DIR / "Control_Asesorias_Tesis_template.xlsm"),
    )


settings = Settings()
