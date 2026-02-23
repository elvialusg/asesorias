"""Utilidades para subir archivos XLSX a Google Drive con una service account."""

from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, Mapping, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveUploader:
    """Pequeño wrapper para enviar archivos al Drive del servicio."""

    def __init__(self, credentials_info: Optional[Dict[str, Any]] = None, folder_id: Optional[str] = None):
        self._credentials_info = credentials_info
        self._folder_id = folder_id

    @classmethod
    def from_streamlit_secrets(cls, secrets: Optional[Mapping[str, Any]]):
        info = None
        folder_id = None
        if secrets:
            creds_section = secrets.get("gcp_service_account")
            if creds_section:
                info = dict(creds_section)
            folder_id = secrets.get("gdrive_folder_id")

        if info is None:
            path = os.getenv("GCP_SERVICE_ACCOUNT_FILE")
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fp:
                    info = json.load(fp)
            folder_id = folder_id or os.getenv("GDRIVE_FOLDER_ID")

        return cls(info, folder_id)

    @property
    def is_configured(self) -> bool:
        return bool(self._credentials_info)

    def upload_excel(self, data: bytes, filename: str) -> Dict[str, str]:
        if not self._credentials_info:
            raise RuntimeError("No hay credenciales configuradas para Google Drive.")

        creds = Credentials.from_service_account_info(self._credentials_info, scopes=DRIVE_SCOPES)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        metadata = {"name": filename}
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
