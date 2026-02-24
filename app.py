"""Punto de entrada de la aplicación Streamlit."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from asesorias_app.ui.app_shell import render_app

st.set_page_config(page_title="Tablero Asesorías (Tesis)", layout="wide")


def configure_google_credentials() -> None:
    """Carga credenciales y variables desde st.secrets cuando se despliega en Streamlit."""
    secrets = st.secrets
    json_key = secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_key:
        creds_path = Path(".streamlit/service-account.json")
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        # Se reescribe cada despliegue efímero de Streamlit Cloud
        creds_path.write_text(json_key)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path.resolve())

    sheet_id = secrets.get("GOOGLE_SHEETS_SPREADSHEET_ID")
    if sheet_id:
        os.environ["GOOGLE_SHEETS_SPREADSHEET_ID"] = sheet_id

    sheet_range = secrets.get("GOOGLE_SHEETS_REGISTRO_RANGE")
    if sheet_range:
        os.environ["GOOGLE_SHEETS_REGISTRO_RANGE"] = sheet_range


def main():
    configure_google_credentials()
    render_app()


if __name__ == "__main__":
    main()
