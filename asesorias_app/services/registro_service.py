"""Servicio con la lógica de negocio del registro."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

import pandas as pd

from asesorias_app import config
from asesorias_app.core.utils import norm_str, normalize_fac_name
from asesorias_app.repositories.excel_repository import ExcelRepository, normalize_registro_df
from asesorias_app.repositories.google_sheets_repository import GoogleSheetsRepository


class RegistroService:
    def __init__(self, repository: Optional[ExcelRepository] = None) -> None:
        if repository is not None:
            self.repo = repository
        elif config.GOOGLE_SHEETS_SPREADSHEET_ID:
            self.repo = GoogleSheetsRepository()
        else:
            self.repo = ExcelRepository()

    @staticmethod
    def _should_update_value(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return norm_str(value) is not None
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, pd.Timestamp):
            return not pd.isna(value)
        return True

    # Helpers --------------------------------------------------------------
    def load_lists(self):
        data = self.repo.load_lists()
        fac_names = data["df_fac"]["Nombre_Facultad"].dropna().astype(str).tolist()
        fac_norm_map = {normalize_fac_name(n): n for n in fac_names}
        data["fac_norm_map"] = fac_norm_map
        return data

    def load_registro(self) -> pd.DataFrame:
        return self.repo.load_registro()

    def save_registro(self, df: pd.DataFrame) -> None:
        self.repo.save_registro(df)

    def download_bytes(self) -> bytes:
        return self.repo.download_current_excel_bytes()

    def build_bulk_template(self, columns: List[str]) -> bytes:
        cols = list(columns)
        if "Paz_y_Salvo" not in cols:
            cols.append("Paz_y_Salvo")
        return self.repo.build_bulk_template(cols)

    # Operaciones ----------------------------------------------------------
    def find_student_index(self, df: pd.DataFrame, cedula: Optional[str], nombre: Optional[str]) -> Optional[int]:
        cedula = norm_str(cedula)
        nombre = norm_str(nombre)
        if cedula and "Cédula" in df.columns:
            match = df[df["Cédula"].astype(str).str.strip() == cedula]
            if not match.empty:
                return int(match.index[0])
        if nombre and "Nombre_Usuario" in df.columns:
            match = df[df["Nombre_Usuario"].astype(str).str.strip().str.lower() == nombre.lower()]
            if not match.empty:
                return int(match.index[0])
        return None

    def add_registro(self, base_row: Dict, asesorias_payload: List[Dict]) -> None:
        df_current = self.load_registro()
        idx = self.find_student_index(df_current, base_row.get("Cédula"), base_row.get("Nombre_Usuario"))
        if idx is not None:
            raise ValueError("El estudiante ya existe.")

        df_new = pd.concat([df_current, pd.DataFrame([base_row])], ignore_index=True)
        self.save_registro(df_new)

    def update_registro(self, base_row: Dict, asesorias_payload: List[Dict]) -> None:
        df_current = self.load_registro()
        idx = self.find_student_index(df_current, base_row.get("Cédula"), base_row.get("Nombre_Usuario"))
        if idx is None:
            raise ValueError("El estudiante no existe.")

        for key, value in base_row.items():
            if key in df_current.columns and self._should_update_value(value):
                df_current.loc[idx, key] = value

        self.save_registro(df_current)

    def delete_registro(self, index_to_delete: int) -> None:
        df = self.load_registro()
        df = df.drop(index=index_to_delete).reset_index(drop=True)
        self.save_registro(df)

    def bulk_import(self, df_upload: pd.DataFrame) -> None:
        df_upload = normalize_registro_df(df_upload.copy())
        df = self.load_registro()
        for _, row in df_upload.iterrows():
            ced = norm_str(row.get("Cédula"))
            nom = norm_str(row.get("Nombre_Usuario"))
            if not ced and not nom:
                continue

            base_row = {}
            for col in df.columns:
                if col in row.index:
                    base_row[col] = row.get(col)

            base_row["Paz_y_Salvo"] = norm_str(row.get("Paz_y_Salvo")) or "EN PROCESO"
            fecha_val = pd.to_datetime(row.get("Fecha"), errors="coerce")
            if pd.isna(fecha_val):
                fecha_val = pd.Timestamp(date.today())
            base_row["Fecha"] = fecha_val

            idx = self.find_student_index(df, ced, nom)
            if idx is None:
                df = pd.concat([df, pd.DataFrame([base_row])], ignore_index=True)
            else:
                for key, value in base_row.items():
                    if key in df.columns and self._should_update_value(value):
                        df.loc[idx, key] = value

        self.save_registro(df)
