"""Configuración global de rutas y constantes."""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_PATH = DATA_DIR / "Control_Asesorias_Tesis_template.xlsm"
DB_PATH = DATA_DIR / "registro_actual.xlsx"

SHEET_REGISTRO = "Registro asesorías"
SHEET_FACULTADES = "Data_Facultades"
SHEET_PROGRAMAS = "Data_Programas"
SHEET_LISTAS = "Insumo_Listas_Desplegables"

ASSETS_DIR = BASE_DIR / "assets"
THEME_CSS = ASSETS_DIR / "styles.css"
