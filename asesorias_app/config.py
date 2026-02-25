"""Configuración global de rutas y constantes."""

from __future__ import annotations

import os
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

_DEFAULT_SERVICE_ACCOUNT = BASE_DIR / "asesorias-488318-60432dd8ea86.json"
# Permite sobreescribir la ubicación mediante la variable de entorno
# GOOGLE_APPLICATION_CREDENTIALS cuando se despliega en la nube.
SERVICE_ACCOUNT_FILE = Path(
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", _DEFAULT_SERVICE_ACCOUNT)
)
SERVICE_ACCOUNT_INFO = None

GOOGLE_SHEETS_SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")
GOOGLE_SHEETS_REGISTRO_RANGE = os.environ.get(
    "GOOGLE_SHEETS_REGISTRO_RANGE", f"{SHEET_REGISTRO}!A:ZZ"
)
GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LEGACY_DETALLE_COLUMN = "Asesor_Metodológico, Modalidad_Asesoría2, Asesor_Metodológico, Modalidad_Asesoría2"
REGISTRO_COLUMNS = [
    "Cédula",
    "Nombre_Usuario",
    "Nombre_Facultad",
    "Nombre_Programa",
    "Modalidad del Programa",
    "Asesor_Recursos_Académicos",
    "Nombre_Asesoría",
    "Modalidad",
    "Asesor_Metodológico",
    "Modalidad_Asesoría2",
    "Título_Trabajo_Grado",
    "Fecha",
    "Revisión Inicial",
    "Revisión plantilla",
    "Ok_Referencistas",
    "OK_Servicios",
    "Observaciones",
    "Escaneado Turnitin",
    "% similitud",
    "Aprobación_Similitud",
    "Total_Asesorías",
    "Historial_Asesorías",
    "Historial_Asesores",
    "Historial_Fechas",
    "Paz_y_Salvo",
    "Paz_y_SSalvo",
    "Historial_Asesor_Recursos",
    "Historial_Asesor_Metodologico",
    "Detalle_Asesor_Metodologico",
]
