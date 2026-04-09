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
GOOGLE_SHEETS_USERS_RANGE = os.environ.get("GOOGLE_SHEETS_USERS_RANGE", "User!A:ZZ")
GOOGLE_SHEETS_FACULTIES_RANGE = os.environ.get("GOOGLE_SHEETS_FACULTIES_RANGE", "UM!A:ZZ")
GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ASSIGNMENT_COLUMN = "Asignado_a"
THESIS_PRIMARY_COLUMN = "Título_Trabajo_Grado"
THESIS_COLUMN_CANDIDATES = [
    "Título_Trabajo_Grado",
    "Titulo_Trabajo_Grado",
    "Título trabajo de grado",
    "Titulo trabajo de grado",
    "Nombre_Tesis",
    "Nombre de tesis",
    "Proyecto",
    "Tesis",
]
THESIS_COLUMN_KEYWORDS = ["tesis", "título", "titulo", "proyecto"]
DEFAULT_ASSIGNMENT_PEOPLE = [
    "Harold Estiven Garía",
    "Luz Andrea Sepúlveda",
    "Juan Pablo Charry",
    "Maria Eugenia Nieto",
]
REGISTRO_ID_COLUMN = "Registro_ID"
NORMALIZATION_STATUS_COLUMN = "Estado_Normalizacion"
NORMALIZATION_REVIEWER_COLUMN = "Revisado_por"
NORMALIZATION_DATE_COLUMN = "Fecha_revision"
NORMALIZATION_OBS_COLUMN = "Observacion_Normalizacion"
NORMALIZATION_OK_VALUE = "OK"
NORMALIZATION_PENDING_VALUE = "Pendiente"

PUBLICATION_ASSIGNMENT_COLUMN = "Asignado_Publicacion"
PUBLICATION_STATUS_COLUMN = "Estado_Publicacion"
PUBLICATION_PUBLISHED_BY_COLUMN = "Publicado_por"
PUBLICATION_DATE_COLUMN = "Fecha_Publicacion"
PUBLICATION_OBS_COLUMN = "Observacion_Publicacion"
PUBLICATION_RESPONSIBLES = [
    "Gloria Patricia Quintero",
    "Diana Patricia Salazar",
]
PUBLICATION_PRIMARY = PUBLICATION_RESPONSIBLES[0]
PUBLICATION_PENDING_VALUE = "Pendiente"
PUBLICATION_DONE_VALUE = "Publicado"

REGISTRO_COLUMNS = [
    "Cédula",
    "Nombre_Usuario",
    "Correo_Electronico",
    "Nombre_Facultad",
    "Nombre_Programa",
    "Modalidad del Programa",
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
    "Paz_y_Salvo",
    ASSIGNMENT_COLUMN,
    NORMALIZATION_STATUS_COLUMN,
    NORMALIZATION_REVIEWER_COLUMN,
    NORMALIZATION_DATE_COLUMN,
    NORMALIZATION_OBS_COLUMN,
    PUBLICATION_ASSIGNMENT_COLUMN,
    PUBLICATION_STATUS_COLUMN,
    PUBLICATION_PUBLISHED_BY_COLUMN,
    PUBLICATION_DATE_COLUMN,
    PUBLICATION_OBS_COLUMN,
]

REMOVED_REGISTRO_COLUMNS = [
    "Modalidad",
    "Modalidad_Asesoría2",
    "Total_Asesorías",
    "Historial_Asesorías",
    "Historial_Asesores",
    "Historial_Fechas",
    "Paz_y_SSalvo",
    "Historial_Asesor_Recursos",
    "Historial_Asesor_Metodologico",
    "Detalle_Asesor_Metodologico",
    "Asesor_Recursos_Académicos",
    "Nombre_Asesoría",
    "Asesor_Metodológico",
]

COLUMN_ALIASES = {
    "Correo electrónico": "Correo_Electronico",
    "Correo electronico": "Correo_Electronico",
    "Cedula": "Cédula",
    "Nombre usuario": "Nombre_Usuario",
    "Nombre_usuario": "Nombre_Usuario",
}
