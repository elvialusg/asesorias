"""Integración con Google Drive usando una service account."""

from __future__ import annotations

import io
from typing import Dict, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveService:
    """Pequeño wrapper para subir archivos XLSX a Google Drive."""

    def __init__(self, credentials_info: Optional[Dict] = None, folder_id: Optional[str] = None):
        self._credentials_info = credentials_info
        self._folder_id = folder_id

    @property
    def is_configured(self) -> bool:
        return bool(self._credentials_info)

    def _client(self):
        if not self._credentials_info:
            raise RuntimeError("No hay credenciales de Google Drive configuradas.")
        creds = Credentials.from_service_account_info(self._credentials_info, scopes=DRIVE_SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def upload_excel(self, data: bytes, file_name: str) -> Dict[str, str]:
        """Sube el Excel y devuelve diccionario con id/link."""
        service = self._client()
        metadata = {"name": file_name}
        if self._folder_id:
            metadata["parents"] = [self._folder_id]
        media = MediaIoBaseUpload(
            io.BytesIO(data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resumable=True,
        )
        created = (
            service.files()
            .create(body=metadata, media_body=media, fields="id, name, webViewLink, webContentLink")
            .execute()
        )
        return {
            "id": created.get("id"),
            "name": created.get("name"),
            "webViewLink": created.get("webViewLink"),
            "webContentLink": created.get("webContentLink"),
        }
