"""Repositorio para interactuar con Google Sheets como fuente principal."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import List

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from asesorias_app import config
from asesorias_app.repositories.excel_repository import ExcelRepository, normalize_registro_df


class GoogleSheetsRepository(ExcelRepository):
    """Implementa las operaciones de registro usando Google Sheets."""

    def __init__(
        self,
        spreadsheet_id: str | None = None,
        credentials_file: Path | None = None,
        registro_range: str | None = None,
    ) -> None:
        super().__init__()
        self.spreadsheet_id = (spreadsheet_id or config.GOOGLE_SHEETS_SPREADSHEET_ID).strip()
        self.credentials_file = Path(credentials_file or config.SERVICE_ACCOUNT_FILE)
        self.registro_range = registro_range or config.GOOGLE_SHEETS_REGISTRO_RANGE
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID no está configurado.")

    def _sheets_service(self):
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

    # Registro principal -------------------------------------------------
    def load_registro(self) -> pd.DataFrame:
        service = self._sheets_service()
        try:
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=self.registro_range)
                .execute()
            )
        except HttpError as exc:
            raise RuntimeError(
                "No se pudo consultar Google Sheets. Verifica que las credenciales tengan acceso al documento."
            ) from exc
        values = result.get("values", [])
        if not values:
            df = pd.DataFrame(columns=[])
        else:
            headers = values[0]
            rows = values[1:]
            normalized_rows: List[List[str]] = []
            for row in rows:
                filled = row + [""] * (len(headers) - len(row))
                normalized_rows.append(filled)
            df = pd.DataFrame(normalized_rows, columns=headers)
        df = normalize_registro_df(df)
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        return df

    def save_registro(self, df: pd.DataFrame) -> None:
        df = df.copy()
        df = normalize_registro_df(df)
        df = df.where(pd.notnull(df), "")
        payload = [list(df.columns)]
        for _, row in df.iterrows():
            payload.append([self._format_value(value) for value in row.tolist()])

        service = self._sheets_service()
        service.spreadsheets().values().clear(
            spreadsheetId=self.spreadsheet_id,
            range=self.registro_range,
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=self.registro_range,
            valueInputOption="RAW",
            body={"values": payload},
        ).execute()

    def download_current_excel_bytes(self) -> bytes:
        return super().download_current_excel_bytes()

    # Helpers ------------------------------------------------------------
    @staticmethod
    def _format_value(value) -> str:
        if value is None:
            return ""
        if isinstance(value, pd.Timestamp):
            if pd.isna(value):
                return ""
            return value.strftime("%Y-%m-%d")
        if isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, float) and pd.isna(value):
            return ""
        return str(value)
