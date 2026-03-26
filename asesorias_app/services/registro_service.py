"""Servicio con la lógica de negocio del registro."""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import uuid4

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

    @staticmethod
    def _is_valid_registro(row) -> bool:
        doc_value = None
        for key in ("CǸdula", "Cédula", "C�dula", "C?dula", "Cedula"):
            if key in row:
                doc_value = row.get(key)
                if doc_value:
                    break
        doc = norm_str(doc_value)
        nombre = norm_str(row.get("Nombre_Usuario"))
        return bool(doc or nombre)

    def distribute_registros(self, responsables: List[str], seed: Optional[int] = None) -> Dict:
        assignment_col = getattr(config, "ASSIGNMENT_COLUMN", "Asignado_a")
        responsables_clean = [r.strip() for r in responsables if r and r.strip()]
        if not responsables_clean:
            raise ValueError("Debes definir al menos una persona responsable.")

        df = self.load_registro()
        if df.empty:
            raise ValueError("No hay registros en el sistema para distribuir.")
        if assignment_col not in df.columns:
            raise RuntimeError(
                f"No existe la columna '{assignment_col}'. Verifica la configuración o ejecuta la normalización primero."
            )

        valid_mask = df.apply(self._is_valid_registro, axis=1)
        df_valid = df.loc[valid_mask].copy()
        ignored = int((~valid_mask).sum())
        if df_valid.empty:
            raise ValueError("No hay registros válidos (con nombre o cédula) para distribuir.")

        shuffled = df_valid.sample(frac=1, random_state=seed)
        counts = {resp: 0 for resp in responsables_clean}
        reps = len(responsables_clean)
        for idx, (row_idx, _) in enumerate(shuffled.iterrows()):
            responsible = responsables_clean[idx % reps]
            df.loc[row_idx, assignment_col] = responsible
            counts[responsible] += 1

        self.save_registro(df)
        return {
            "total_valid": int(len(df_valid)),
            "ignored_rows": ignored,
            "counts": counts,
            "seed": seed,
            "assignment_column": assignment_col,
        }

    def _load_registro_for_normalizacion(self) -> pd.DataFrame:
        df = self.load_registro()
        changed = False
        required = [
            config.ASSIGNMENT_COLUMN,
            config.REGISTRO_ID_COLUMN,
            config.NORMALIZATION_STATUS_COLUMN,
            config.NORMALIZATION_REVIEWER_COLUMN,
            config.NORMALIZATION_DATE_COLUMN,
            config.NORMALIZATION_OBS_COLUMN,
        ]
        for col in required:
            if col not in df.columns:
                df[col] = ""
                changed = True
            else:
                mask = df[col].isna()
                if mask.any():
                    default_value = config.NORMALIZATION_PENDING_VALUE if col == config.NORMALIZATION_STATUS_COLUMN else ""
                    df.loc[mask, col] = default_value
                    changed = True
        status_col = config.NORMALIZATION_STATUS_COLUMN
        if status_col in df.columns:
            empty_status = df[status_col].astype(str).str.strip() == ""
            if empty_status.any():
                df.loc[empty_status, status_col] = config.NORMALIZATION_PENDING_VALUE
                changed = True
        if self._fill_missing_ids(df):
            changed = True
        if changed:
            self.save_registro(df)
        return df

    def _fill_missing_ids(self, df: pd.DataFrame) -> bool:
        id_col = config.REGISTRO_ID_COLUMN
        if id_col not in df.columns:
            df[id_col] = ""
            return True
        mask = df[id_col].astype(str).str.strip().isin(["", "nan", "None"])
        if not mask.any():
            return False
        df.loc[mask, id_col] = [str(uuid4()) for _ in range(mask.sum())]
        return True

    @staticmethod
    def _cedula_column(df: pd.DataFrame) -> Optional[str]:
        for candidate in ("CǸdula", "Cédula", "C?dula", "Cedula"):
            if candidate in df.columns:
                return candidate
        return None

    def list_responsables(self) -> List[str]:
        df = self._load_registro_for_normalizacion()
        assignment_col = config.ASSIGNMENT_COLUMN
        existing = df[assignment_col].dropna().astype(str).str.strip().tolist() if assignment_col in df.columns else []
        ordered: List[str] = []
        for name in (config.DEFAULT_ASSIGNMENT_PEOPLE + existing):
            clean = norm_str(name)
            if clean and clean not in ordered:
                ordered.append(clean)
        return ordered

    def _filter_by_responsable(self, df: pd.DataFrame, responsable: str) -> pd.DataFrame:
        assignment_col = config.ASSIGNMENT_COLUMN
        target = norm_str(responsable)
        if not target:
            return df.iloc[0:0].copy()
        values = df[assignment_col].fillna("").astype(str)
        mask = values.apply(lambda v: (norm_str(v) or "").lower()) == target.lower()
        return df.loc[mask].copy()

    def get_registros_por_responsable(self, responsable: str) -> pd.DataFrame:
        df = self._load_registro_for_normalizacion()
        return self._filter_by_responsable(df, responsable)

    def build_responsable_excel(self, responsable: str) -> bytes:
        df_resp = self.get_registros_por_responsable(responsable)
        if df_resp.empty:
            raise ValueError("No hay registros asignados a esta persona")
        columns = [config.REGISTRO_ID_COLUMN, "Nombre_Usuario"]
        ced_col = self._cedula_column(df_resp)
        if ced_col:
            columns.append(ced_col)
        columns += [
            config.ASSIGNMENT_COLUMN,
            config.NORMALIZATION_STATUS_COLUMN,
            config.NORMALIZATION_OBS_COLUMN,
            config.NORMALIZATION_REVIEWER_COLUMN,
            config.NORMALIZATION_DATE_COLUMN,
        ]
        columns = [col for col in columns if col in df_resp.columns]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_resp[columns].to_excel(writer, index=False, sheet_name="Asignados")
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def summarize_normalizacion(df: pd.DataFrame) -> Dict[str, int]:
        status_col = config.NORMALIZATION_STATUS_COLUMN
        ok_value = (config.NORMALIZATION_OK_VALUE or "OK").upper()
        status = df[status_col].fillna("").astype(str).str.upper() if status_col in df.columns else pd.Series(dtype=str)
        ok = int((status == ok_value).sum())
        total = int(len(df))
        pending = total - ok
        return {"total": total, "ok": ok, "pending": pending}

    def update_normalizacion_estado(self, responsable: str, updates: List[Dict]) -> Dict:
        df = self._load_registro_for_normalizacion()
        id_col = config.REGISTRO_ID_COLUMN
        assignment_col = config.ASSIGNMENT_COLUMN
        status_col = config.NORMALIZATION_STATUS_COLUMN
        reviewer_col = config.NORMALIZATION_REVIEWER_COLUMN
        date_col = config.NORMALIZATION_DATE_COLUMN
        obs_col = config.NORMALIZATION_OBS_COLUMN
        updated = 0
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        target_name = (norm_str(responsable) or "").lower()
        for item in updates:
            uid = norm_str(item.get("id") or item.get(id_col))
            if not uid:
                continue
            matches = df[df[id_col].astype(str) == uid].index
            if matches.empty:
                continue
            idx = matches[0]
            assigned = (norm_str(df.at[idx, assignment_col]) or "").lower()
            if assigned != target_name:
                continue
            marked_ok = bool(item.get("ok"))
            target_status = config.NORMALIZATION_OK_VALUE if marked_ok else config.NORMALIZATION_PENDING_VALUE
            obs_text = norm_str(item.get("observacion")) or ""
            changed = False
            if str(df.at[idx, status_col]) != target_status:
                df.at[idx, status_col] = target_status
                changed = True
            if str(df.at[idx, obs_col]) != obs_text:
                df.at[idx, obs_col] = obs_text
                changed = True
            if marked_ok:
                if str(df.at[idx, reviewer_col]) != responsable:
                    df.at[idx, reviewer_col] = responsable
                    changed = True
                df.at[idx, date_col] = timestamp
            else:
                if str(df.at[idx, reviewer_col]):
                    df.at[idx, reviewer_col] = ""
                    changed = True
                if str(df.at[idx, date_col]):
                    df.at[idx, date_col] = ""
                    changed = True
            if changed:
                updated += 1
        if updated:
            self.save_registro(df)
        summary_df = self._filter_by_responsable(df, responsable)
        summary = self.summarize_normalizacion(summary_df)
        summary["updated"] = updated
        return summary
