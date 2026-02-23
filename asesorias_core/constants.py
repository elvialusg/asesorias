"""Constantes y mapeos reutilizables en la aplicación."""

from __future__ import annotations

from collections import OrderedDict

# Columnas canónicas usadas en el Streamlit y servicios
COL_NOMBRE_FACULTAD = "Nombre_Facultad"
COL_NOMBRE_PROGRAMA = "Nombre_Programa"
COL_CEDULA = "Cedula"
COL_NOMBRE_USUARIO = "Nombre_Usuario"
COL_ASESOR_RECURSOS = "Asesor_Recursos_Academicos"
COL_NOMBRE_ASESORIA = "Nombre_Asesoria"
COL_MODALIDAD = "Modalidad"
COL_ASESOR_METODOLOGICO_DETALLE = "Asesor_Metodologico_Detalle"
COL_TITULO_TRABAJO = "Titulo_Trabajo_Grado"
COL_FECHA = "Fecha"
COL_REVISION_INICIAL = "Revision_Inicial"
COL_REVISION_PLANTILLA = "Revision_Plantilla"
COL_OK_REFERENCISTAS = "Ok_Referencistas"
COL_OK_SERVICIOS = "OK_Servicios"
COL_OBSERVACIONES = "Observaciones"
COL_ESCANEADO_TURNITIN = "Escaneado_Turnitin"
COL_PORCENTAJE_SIMILITUD = "Porcentaje_Similitud"
COL_APROBACION_SIMILITUD = "Aprobacion_Similitud"
COL_MODALIDAD_PROGRAMA = "Modalidad_Programa"
COL_TOTAL_ASESORIAS = "Total_Asesorias"
COL_HISTORIAL_ASESORIAS = "Historial_Asesorias"
COL_HISTORIAL_ASESOR_RECURSOS = "Historial_Asesor_Recursos"
COL_HISTORIAL_ASESOR_METODOLOGICO = "Historial_Asesor_Metodologico"
COL_HISTORIAL_FECHAS = "Historial_Fechas"
COL_PAZ_Y_SALVO = "Paz_y_Salvo"

BASE_COLUMNS = OrderedDict(
    [
        ("id", "id"),
        ("nombre_facultad", COL_NOMBRE_FACULTAD),
        ("nombre_programa", COL_NOMBRE_PROGRAMA),
        ("cedula", COL_CEDULA),
        ("nombre_usuario", COL_NOMBRE_USUARIO),
        ("asesor_recursos_academicos", COL_ASESOR_RECURSOS),
        ("nombre_asesoria", COL_NOMBRE_ASESORIA),
        ("modalidad", COL_MODALIDAD),
        ("asesor_metodologico_detalle", COL_ASESOR_METODOLOGICO_DETALLE),
        ("titulo_trabajo_grado", COL_TITULO_TRABAJO),
        ("fecha", COL_FECHA),
        ("revision_inicial", COL_REVISION_INICIAL),
        ("revision_plantilla", COL_REVISION_PLANTILLA),
        ("ok_referencistas", COL_OK_REFERENCISTAS),
        ("ok_servicios", COL_OK_SERVICIOS),
        ("observaciones", COL_OBSERVACIONES),
        ("escaneado_turnitin", COL_ESCANEADO_TURNITIN),
        ("porcentaje_similitud", COL_PORCENTAJE_SIMILITUD),
        ("aprobacion_similitud", COL_APROBACION_SIMILITUD),
        ("modalidad_programa", COL_MODALIDAD_PROGRAMA),
        ("total_asesorias", COL_TOTAL_ASESORIAS),
        ("historial_asesorias", COL_HISTORIAL_ASESORIAS),
        ("historial_asesor_recursos", COL_HISTORIAL_ASESOR_RECURSOS),
        ("historial_asesor_metodologico", COL_HISTORIAL_ASESOR_METODOLOGICO),
        ("historial_fechas", COL_HISTORIAL_FECHAS),
        ("paz_y_salvo", COL_PAZ_Y_SALVO),
    ]
)

EXTRA_COLUMNS = [
    COL_TOTAL_ASESORIAS,
    COL_HISTORIAL_ASESORIAS,
    COL_HISTORIAL_FECHAS,
    COL_HISTORIAL_ASESOR_RECURSOS,
    COL_HISTORIAL_ASESOR_METODOLOGICO,
    COL_PAZ_Y_SALVO,
]

# Mapa para traducir encabezados legados (con tildes o caracteres dañados)
LEGACY_COLUMN_MAP = {
    "Nombre_Facultad": COL_NOMBRE_FACULTAD,
    "Nombre_Programa": COL_NOMBRE_PROGRAMA,
    "Cédula": COL_CEDULA,
    "C�dula": COL_CEDULA,
    "CǸdula": COL_CEDULA,
    "Nombre_Usuario": COL_NOMBRE_USUARIO,
    "Asesor_Recursos_Académicos": COL_ASESOR_RECURSOS,
    "Asesor_Recursos_Acad�micos": COL_ASESOR_RECURSOS,
    "Nombre_Asesoría": COL_NOMBRE_ASESORIA,
    "Nombre_Asesor�a": COL_NOMBRE_ASESORIA,
    "Modalidad": COL_MODALIDAD,
    "Modalidad del Programa": COL_MODALIDAD_PROGRAMA,
    "Asesor_Metodológico, Modalidad_Asesoría2, Asesor_Metodológico, Modalidad_Asesoría2": COL_ASESOR_METODOLOGICO_DETALLE,
    "Asesor_Metodol�gico, Modalidad_Asesor�a2, Asesor_Metodol�gico, Modalidad_Asesor�a2": COL_ASESOR_METODOLOGICO_DETALLE,
    "Asesor_Metodológico": COL_ASESOR_METODOLOGICO_DETALLE,
    "T�tulo_Trabajo_Grado": COL_TITULO_TRABAJO,
    "Título_Trabajo_Grado": COL_TITULO_TRABAJO,
    "Fecha": COL_FECHA,
    "Revisión Inicial": COL_REVISION_INICIAL,
    "Revisi�n Inicial": COL_REVISION_INICIAL,
    "Revisión plantilla": COL_REVISION_PLANTILLA,
    "Revisi�n plantilla": COL_REVISION_PLANTILLA,
    "Ok_Referencistas": COL_OK_REFERENCISTAS,
    "OK_Servicios": COL_OK_SERVICIOS,
    "Observaciones": COL_OBSERVACIONES,
    "Escaneado Turnitin": COL_ESCANEADO_TURNITIN,
    "% similitud": COL_PORCENTAJE_SIMILITUD,
    "Aprobación_Similitud": COL_APROBACION_SIMILITUD,
    "Aprobaci�n_Similitud": COL_APROBACION_SIMILITUD,
    "Modalidad del Programa": COL_MODALIDAD_PROGRAMA,
    "Total_Asesorías": COL_TOTAL_ASESORIAS,
    "Total_Asesor�as": COL_TOTAL_ASESORIAS,
    "Historial_Asesorías": COL_HISTORIAL_ASESORIAS,
    "Historial_Asesor�as": COL_HISTORIAL_ASESORIAS,
    "Historial_Asesor_Recursos": COL_HISTORIAL_ASESOR_RECURSOS,
    "Historial_Asesor_Metodologico": COL_HISTORIAL_ASESOR_METODOLOGICO,
    "Historial_Fechas": COL_HISTORIAL_FECHAS,
    "Paz_y_Salvo": COL_PAZ_Y_SALVO,
    "Paz_y_SSalvo": COL_PAZ_Y_SALVO,
}


def normalize_column_name(name: str) -> str:
    """Convierte un encabezado legado al nombre estándar."""
    return LEGACY_COLUMN_MAP.get(name, name)
