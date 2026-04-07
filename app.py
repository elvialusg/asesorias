"""Punto de entrada de la aplicacion Streamlit."""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from asesorias_app import config
from asesorias_app.auth import service as auth_service
from asesorias_app.ui.app_shell import render_app

st.set_page_config(page_title="Controltesis", layout="wide")


def configure_google_credentials() -> None:
    """Carga credenciales y variables desde st.secrets cuando se despliega en Streamlit."""
    secrets = st.secrets
    json_key = secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_key:
        if isinstance(json_key, str):
            raw_text = json_key.strip()
            try:
                json_body = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "El secret GOOGLE_SERVICE_ACCOUNT_JSON no es un JSON valido."
                ) from exc
        elif isinstance(json_key, dict):
            json_body = json_key
        else:
            json_body = json.loads(json_key)
        private_key = json_body.get("private_key")
        if isinstance(private_key, str) and "\\n" in private_key:
            json_body["private_key"] = private_key.replace("\\n", "\n")
        json_content = json.dumps(json_body)
        creds_path = Path(".streamlit/service-account.json")
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        creds_path.write_text(json_content)
        resolved = str(creds_path.resolve())
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = resolved
        config.SERVICE_ACCOUNT_FILE = Path(resolved)
        config.SERVICE_ACCOUNT_INFO = json_body

    sheet_id = secrets.get("GOOGLE_SHEETS_SPREADSHEET_ID")
    if sheet_id:
        os.environ["GOOGLE_SHEETS_SPREADSHEET_ID"] = sheet_id
        config.GOOGLE_SHEETS_SPREADSHEET_ID = sheet_id

    sheet_range = secrets.get("GOOGLE_SHEETS_REGISTRO_RANGE")
    if sheet_range:
        os.environ["GOOGLE_SHEETS_REGISTRO_RANGE"] = sheet_range
        config.GOOGLE_SHEETS_REGISTRO_RANGE = sheet_range


def main():
    configure_google_credentials()
    auth_service.ensure_default_users()
    render_app()


if __name__ == "__main__":
    main()
