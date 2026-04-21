"""Repositorio para gestionar los usuarios desde Google Sheets."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from asesorias_app import config
from asesorias_app.core.utils import fix_text_encoding

DEFAULT_HEADERS = [
    "email",
    "name",
    "role",
    "password_hash",
    "must_reset",
    "reset_token",
    "reset_token_expire",
]


class UserSheetRepository:
    """Lee y escribe los usuarios autorizados directamente en Google Sheets."""

    def __init__(
        self,
        spreadsheet_id: str | None = None,
        credentials_file: Path | None = None,
        users_range: str | None = None,
    ) -> None:
        self.spreadsheet_id = (spreadsheet_id or config.GOOGLE_SHEETS_SPREADSHEET_ID).strip()
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID no esta configurado.")
        self.credentials_file = Path(credentials_file or config.SERVICE_ACCOUNT_FILE)
        self.users_range = users_range or config.GOOGLE_SHEETS_USERS_RANGE
        self._headers: List[str] | None = None

    def _service(self):
        if config.SERVICE_ACCOUNT_INFO:
            creds = service_account.Credentials.from_service_account_info(
                config.SERVICE_ACCOUNT_INFO,
                scopes=config.GOOGLE_SHEETS_SCOPES,
            )
        else:
            if not self.credentials_file.exists():
                raise FileNotFoundError(f"No se encuentra la credencial: {self.credentials_file}")
            creds = service_account.Credentials.from_service_account_file(
                str(self.credentials_file),
                scopes=config.GOOGLE_SHEETS_SCOPES,
            )
        return build("sheets", "v4", credentials=creds, cache_discovery=False)

    @staticmethod
    def _normalize_header(name: str) -> str:
        text = fix_text_encoding(name, strip=True) or ""
        text = text.lower().replace(" ", "_")
        if text in ("correo", "correo_institucional"):
            return "email"
        if text in (
            "contraseña",
            "contraseã±a",
            "contrasena",
            "clave",
            "password",
            "passwordhash",
            "password_hash",
            "contraseña_asignada",
            "contrasena_asignada",
            "clave_asignada",
        ):
            return "password_hash"
        if "contraseña" in text or "contrasena" in text or "password" in text or text.startswith("clave"):
            return "password_hash"
        if text in ("nombre", "usuario", "nombre_usuario"):
            return "name"
        if text in ("rol", "perfil"):
            return "role"
        return text

    def load_users(self) -> List[Dict[str, str]]:
        service = self._service()
        try:
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=self.users_range)
                .execute()
            )
        except HttpError as exc:  # pragma: no cover - dependiente de red
            raise RuntimeError("No se pudo consultar la hoja de usuarios en Google Sheets.") from exc
        rows = result.get("values", [])
        if not rows:
            self._headers = DEFAULT_HEADERS.copy()
            return []
        headers = [fix_text_encoding(col, strip=True) or "" for col in rows[0]]
        if not headers:
            headers = DEFAULT_HEADERS.copy()
        self._headers = headers
        normalized_headers = [self._normalize_header(header) for header in headers]
        records: List[Dict[str, str]] = []
        for row in rows[1:]:
            record: Dict[str, str] = {}
            for idx, key in enumerate(normalized_headers):
                if not key:
                    continue
                value = row[idx] if idx < len(row) else ""
                record[key] = value
            records.append(record)
        return records

    def save_users(self, records: List[Dict[str, str]]) -> None:
        headers = self._headers or DEFAULT_HEADERS
        normalized_headers = [self._normalize_header(name) for name in headers]
        payload: List[List[str]] = [headers]
        for record in records:
            row: List[str] = []
            for key in normalized_headers:
                if not key:
                    row.append("")
                    continue
                row.append(self._format_value(record.get(key, "")))
            payload.append(row)
        service = self._service()
        service.spreadsheets().values().clear(
            spreadsheetId=self.spreadsheet_id,
            range=self.users_range,
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=self.users_range,
            valueInputOption="RAW",
            body={"values": payload},
        ).execute()

    @staticmethod
    def _format_value(value) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        return str(value)
