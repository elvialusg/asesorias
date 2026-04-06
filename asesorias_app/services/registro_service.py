"""Servicio con la lógica de negocio del registro."""

from __future__ import annotations

import io
from datetime import date, datetime
import random
from typing import Dict, List, Optional
import pandas as pd

from asesorias_app import config
from asesorias_app.core.utils import fix_text_encoding, norm_str, normalize_fac_name
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
        normalized_row = {
            (fix_text_encoding(col, strip=True) or "").lower(): value for col, value in row.items()
        }
        for key in ("CǸdula", "Cédula", "C?dula", "Cedula"):
            normalized_key = (fix_text_encoding(key, strip=True) or "").lower()
            if normalized_key in normalized_row:
                doc_value = normalized_row[normalized_key]
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

        thesis_col = self._tesis_column(df)
        if not thesis_col:
            raise RuntimeError(
                "No encuentro una columna que identifique la tesis. "
                "Verifica la configuración de THESIS_PRIMARY_COLUMN o agrega una columna de título."
            )

        valid_mask = df.apply(self._is_valid_registro, axis=1)
        df_valid = df.loc[valid_mask].copy()
        ignored = int((~valid_mask).sum())
        if df_valid.empty:
            raise ValueError("No hay registros válidos (con nombre o cédula) para distribuir.")

        thesis_groups = self._build_tesis_groups(df_valid, thesis_col)
        if not thesis_groups:
            raise ValueError("No hay tesis para distribuir.")

        rng = random.Random(seed)
        rng.shuffle(thesis_groups)
        counts = {resp: {"tesis": 0, "estudiantes": 0} for resp in responsables_clean}
        reps = len(responsables_clean)
        for idx, group in enumerate(thesis_groups):
            responsible = responsables_clean[idx % reps]
            df.loc[group["indices"], assignment_col] = responsible
            counts[responsible]["tesis"] += 1
            counts[responsible]["estudiantes"] += group["students"]

        self.save_registro(df)
        total_students = sum(group["students"] for group in thesis_groups)
        thesis_without_title = sum(1 for group in thesis_groups if group["sin_titulo"])
        return {
            "total_valid": int(len(df_valid)),
            "ignored_rows": ignored,
            "counts": counts,
            "seed": seed,
            "assignment_column": assignment_col,
            "thesis_column": thesis_col,
            "total_thesis": len(thesis_groups),
            "total_students": total_students,
            "thesis_without_title": thesis_without_title,
        }

    def _load_registro_for_normalizacion(self) -> pd.DataFrame:
        df = self.load_registro()
        changed = False
        required = [
            config.ASSIGNMENT_COLUMN,
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
        registro_id_col = config.REGISTRO_ID_COLUMN
        if registro_id_col in df.columns:
            df = df.drop(columns=[registro_id_col])
            changed = True
        if changed:
            self.save_registro(df)
        return df

    @staticmethod
    def _cedula_column(df: pd.DataFrame) -> Optional[str]:
        normalized_columns = {
            (fix_text_encoding(col, strip=True) or "").lower(): col for col in df.columns
        }
        for candidate in ("CǸdula", "Cédula", "C?dula", "Cedula"):
            normalized_candidate = (fix_text_encoding(candidate, strip=True) or "").lower()
            match = normalized_columns.get(normalized_candidate)
            if match:
                return match
        return None

    @staticmethod
    def _tesis_column(df: pd.DataFrame) -> Optional[str]:
        configured = getattr(config, "THESIS_PRIMARY_COLUMN", None)
        candidates = []
        if configured:
            candidates.append(configured)
        candidates.extend(getattr(config, "THESIS_COLUMN_CANDIDATES", []))
        seen = set()
        ordered_candidates = []
        for col in candidates:
            if not col or col in seen:
                continue
            ordered_candidates.append(col)
            seen.add(col)
        for candidate in ordered_candidates:
            if candidate in df.columns:
                return candidate
        keywords = getattr(config, "THESIS_COLUMN_KEYWORDS", [])
        for col in df.columns:
            lowered = col.lower()
            if any(keyword in lowered for keyword in keywords):
                return col
        return None

    @staticmethod
    def _build_tesis_groups(df: pd.DataFrame, thesis_col: str) -> List[Dict]:
        groups = {}
        thesisless_rows = []
        for row_idx, row in df.iterrows():
            thesis_value = norm_str(row.get(thesis_col))
            if thesis_value:
                groups.setdefault(thesis_value, []).append(row_idx)
            else:
                thesisless_rows.append(row_idx)
        grouped = [
            {"tesis": tesis, "indices": indices, "students": len(indices), "sin_titulo": False}
            for tesis, indices in groups.items()
        ]
        for counter, row_idx in enumerate(thesisless_rows, 1):
            grouped.append(
                {
                    "tesis": f"Tesis sin título #{counter}",
                    "indices": [row_idx],
                    "students": 1,
                    "sin_titulo": True,
                }
            )
        return grouped

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

    def _ensure_publicacion_columns(self, df: pd.DataFrame) -> bool:
        changed = False
        defaults = {
            config.PUBLICATION_ASSIGNMENT_COLUMN: config.PUBLICATION_PRIMARY,
            config.PUBLICATION_STATUS_COLUMN: config.PUBLICATION_PENDING_VALUE,
            config.PUBLICATION_PUBLISHED_BY_COLUMN: "",
            config.PUBLICATION_DATE_COLUMN: "",
            config.PUBLICATION_OBS_COLUMN: "",
        }
        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = default
                changed = True
            else:
                mask = df[col].isna()
                if mask.any():
                    df.loc[mask, col] = default
                    changed = True
        assign_col = config.PUBLICATION_ASSIGNMENT_COLUMN
        primary = config.PUBLICATION_PRIMARY
        if assign_col in df.columns and primary:
            empty_assign = df[assign_col].astype(str).str.strip() == ""
            if empty_assign.any():
                df.loc[empty_assign, assign_col] = primary
                changed = True
        status_col = config.PUBLICATION_STATUS_COLUMN
        if status_col in df.columns:
            empty_status = df[status_col].astype(str).str.strip() == ""
            if empty_status.any():
                df.loc[empty_status, status_col] = config.PUBLICATION_PENDING_VALUE
                changed = True
        return changed

    def _load_registro_for_publicacion(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        df = self._load_registro_for_normalizacion()
        changed = self._ensure_publicacion_columns(df)
        status_col = config.NORMALIZATION_STATUS_COLUMN
        ok_value = (config.NORMALIZATION_OK_VALUE or "OK").upper()
        status = df[status_col].fillna("").astype(str).str.upper()
        ready_mask = status == ok_value
        ready_df = df.loc[ready_mask].copy()
        if changed:
            self.save_registro(df)
        return df, ready_df

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
        columns = ["Nombre_Usuario"]
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
        index_lookup = {str(idx): idx for idx in df.index}
        for item in updates:
            uid = norm_str(item.get("id") or item.get(id_col))
            if not uid:
                continue
            idx = index_lookup.get(uid)
            if idx is None:
                continue
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

    def list_publicacion_responsables(self) -> List[str]:
        return list(config.PUBLICATION_RESPONSIBLES)

    def _filter_publicacion_by_responsable(self, df: pd.DataFrame, responsable: str) -> pd.DataFrame:
        assignment_col = config.PUBLICATION_ASSIGNMENT_COLUMN
        target = norm_str(responsable)
        if not target:
            return df.iloc[0:0].copy()
        values = df[assignment_col].fillna("").astype(str)
        mask = values.apply(lambda v: (norm_str(v) or "").lower()) == target.lower()
        return df.loc[mask].copy()

    def get_publicacion_registros(
        self,
        responsable: Optional[str] = None,
        *,
        include_all_for_primary: bool = False,
        only_pending: bool = False,
    ) -> pd.DataFrame:
        _, ready_df = self._load_registro_for_publicacion()
        df_target = ready_df
        if responsable:
            target_norm = (norm_str(responsable) or "").lower()
            primary_norm = (norm_str(config.PUBLICATION_PRIMARY) or "").lower()
            if not (include_all_for_primary and target_norm == primary_norm):
                df_target = self._filter_publicacion_by_responsable(df_target, responsable)
        if only_pending:
            state_col = config.PUBLICATION_STATUS_COLUMN
            done_value = (config.PUBLICATION_DONE_VALUE or "Publicado").upper()
            state = df_target[state_col].fillna("").astype(str).str.upper()
            df_target = df_target[state != done_value]
        return df_target

    def build_publicacion_excel(
        self, responsable: Optional[str], include_all_for_primary: bool = False
    ) -> bytes:
        df_resp = self.get_publicacion_registros(
            responsable, include_all_for_primary=include_all_for_primary
        )
        if df_resp.empty:
            raise ValueError("No hay registros de publicacion para descargar con este filtro")
        columns = ["Nombre_Usuario"]
        ced_col = self._cedula_column(df_resp)
        if ced_col:
            columns.append(ced_col)
        columns += [
            config.PUBLICATION_ASSIGNMENT_COLUMN,
            config.PUBLICATION_STATUS_COLUMN,
            config.PUBLICATION_OBS_COLUMN,
            config.PUBLICATION_PUBLISHED_BY_COLUMN,
            config.PUBLICATION_DATE_COLUMN,
        ]
        columns = [col for col in columns if col in df_resp.columns]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_resp[columns].to_excel(writer, index=False, sheet_name="Publicacion")
        buffer.seek(0)
        return buffer.read()

    def assign_publicacion(self, assigner: str, ids: List[str], target: str) -> int:
        primary_norm = (norm_str(config.PUBLICATION_PRIMARY) or "").lower()
        assigner_norm = (norm_str(assigner) or "").lower()
        if assigner_norm != primary_norm:
            raise PermissionError("Solo la responsable principal puede reasignar publicaciones.")
        target_clean = norm_str(target)
        allowed = [norm_str(r) for r in config.PUBLICATION_RESPONSIBLES]
        if target_clean not in allowed:
            raise ValueError("Responsable de publicacion no valido.")
        df_all, ready_df = self._load_registro_for_publicacion()
        assignment_col = config.PUBLICATION_ASSIGNMENT_COLUMN
        state_col = config.PUBLICATION_STATUS_COLUMN
        pub_by_col = config.PUBLICATION_PUBLISHED_BY_COLUMN
        date_col = config.PUBLICATION_DATE_COLUMN
        obs_col = config.PUBLICATION_OBS_COLUMN
        allowed_ids = {str(idx) for idx in ready_df.index}
        index_lookup = {str(idx): idx for idx in df_all.index}
        normalized_ids = [norm_str(i) for i in ids if norm_str(i)]
        updated = 0
        for uid in normalized_ids:
            if uid not in allowed_ids:
                continue
            idx = index_lookup.get(uid)
            if idx is None:
                continue
            df_all.at[idx, assignment_col] = target
            df_all.at[idx, state_col] = config.PUBLICATION_PENDING_VALUE
            df_all.at[idx, pub_by_col] = ""
            df_all.at[idx, date_col] = ""
            if pd.isna(df_all.at[idx, obs_col]):
                df_all.at[idx, obs_col] = ""
            updated += 1
        if updated:
            self.save_registro(df_all)
        return updated

    def summarize_publicacion(self, df: pd.DataFrame) -> Dict:
        state_col = config.PUBLICATION_STATUS_COLUMN
        assignment_col = config.PUBLICATION_ASSIGNMENT_COLUMN
        done_value = (config.PUBLICATION_DONE_VALUE or "Publicado").upper()
        state = df[state_col].fillna("").astype(str).str.upper() if state_col in df.columns else pd.Series(dtype=str)
        total = int(len(df))
        published = int((state == done_value).sum())
        pending = total - published
        assigned: Dict[str, int] = {}
        for resp in config.PUBLICATION_RESPONSIBLES:
            assigned[resp] = int(
                (
                    df[assignment_col]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    == (norm_str(resp) or "").lower()
                ).sum()
            )
        return {"total": total, "published": published, "pending": pending, "assigned": assigned}

    def update_publicacion_estado(self, responsable: str, updates: List[Dict]) -> Dict:
        df_all, ready_df = self._load_registro_for_publicacion()
        assignment_col = config.PUBLICATION_ASSIGNMENT_COLUMN
        state_col = config.PUBLICATION_STATUS_COLUMN
        pub_by_col = config.PUBLICATION_PUBLISHED_BY_COLUMN
        date_col = config.PUBLICATION_DATE_COLUMN
        obs_col = config.PUBLICATION_OBS_COLUMN
        target_norm = (norm_str(responsable) or "").lower()
        allowed = {str(idx) for idx in ready_df.index}
        index_lookup = {str(idx): idx for idx in df_all.index}
        updated = 0
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        done_value = config.PUBLICATION_DONE_VALUE
        pending_value = config.PUBLICATION_PENDING_VALUE
        for item in updates:
            uid = norm_str(item.get("id"))
            if not uid or uid not in allowed:
                continue
            idx = index_lookup.get(uid)
            if idx is None:
                continue
            assigned = (norm_str(df_all.at[idx, assignment_col]) or "").lower()
            if assigned != target_norm:
                continue
            marked = bool(item.get("ok"))
            obs_text = norm_str(item.get("observacion")) or ""
            changed = False
            new_status = done_value if marked else pending_value
            if str(df_all.at[idx, state_col]) != new_status:
                df_all.at[idx, state_col] = new_status
                changed = True
            if str(df_all.at[idx, obs_col]) != obs_text:
                df_all.at[idx, obs_col] = obs_text
                changed = True
            if marked:
                if str(df_all.at[idx, pub_by_col]) != responsable:
                    df_all.at[idx, pub_by_col] = responsable
                    changed = True
                df_all.at[idx, date_col] = timestamp
            else:
                if str(df_all.at[idx, pub_by_col]):
                    df_all.at[idx, pub_by_col] = ""
                    changed = True
                if str(df_all.at[idx, date_col]):
                    df_all.at[idx, date_col] = ""
                    changed = True
            if changed:
                updated += 1
        if updated:
            self.save_registro(df_all)
        resumen = self.get_publicacion_registros(responsable)
        summary = self.summarize_publicacion(resumen)
        summary["updated"] = updated
        return summary

    def build_dashboard_dataframe(self) -> pd.DataFrame:
        df_all, _ = self._load_registro_for_publicacion()
        df = df_all.copy()
        for col in ["Fecha", config.NORMALIZATION_DATE_COLUMN, config.PUBLICATION_DATE_COLUMN]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def filter_dashboard_dataframe(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        responsables: Optional[List[str]] = None,
        estados: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        filtered = df.copy()
        if start_date and "Fecha" in filtered.columns:
            filtered = filtered[filtered["Fecha"] >= pd.Timestamp(start_date)]
        if end_date and "Fecha" in filtered.columns:
            filtered = filtered[filtered["Fecha"] <= pd.Timestamp(end_date)]
        if responsables:
            normalized_targets = {(norm_str(r) or "").lower() for r in responsables}
            assignment_col = config.ASSIGNMENT_COLUMN
            if assignment_col in filtered.columns:
                filtered = filtered[
                    filtered[assignment_col]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .isin(normalized_targets)
                ]
        if estados:
            status_col = config.PUBLICATION_STATUS_COLUMN
            if status_col in filtered.columns:
                estados_norm = {(norm_str(e) or "").lower() for e in estados}
                filtered = filtered[
                    filtered[status_col]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .isin(estados_norm)
                ]
        return filtered

    def _dashboard_vectors(self, df: pd.DataFrame):
        norm_status_col = config.NORMALIZATION_STATUS_COLUMN
        if norm_status_col in df.columns:
            norm_status = df[norm_status_col].fillna("").astype(str).str.upper()
        else:
            norm_status = pd.Series([""] * len(df), index=df.index)

        pub_status_col = config.PUBLICATION_STATUS_COLUMN
        if pub_status_col in df.columns:
            pub_status = df[pub_status_col].fillna("").astype(str).str.upper()
        else:
            pub_status = pd.Series([""] * len(df), index=df.index)

        obs_col = config.NORMALIZATION_OBS_COLUMN
        general_obs_col = "Observaciones"
        obs_mask = pd.Series(False, index=df.index, dtype=bool)
        if obs_col in df.columns:
            obs_mask |= df[obs_col].fillna("").astype(str).str.strip() != ""
        if general_obs_col in df.columns:
            obs_mask |= df[general_obs_col].fillna("").astype(str).str.strip() != ""
        return norm_status, pub_status, obs_mask

    def calculate_dashboard_metrics(self, df: pd.DataFrame) -> Dict:
        norm_status, pub_status, obs_mask = self._dashboard_vectors(df)
        total = int(len(df))
        norm_ok = (config.NORMALIZATION_OK_VALUE or "OK").upper()
        norm_ok_count = int((norm_status == norm_ok).sum())
        pub_done = (config.PUBLICATION_DONE_VALUE or "PUBLICADO").upper()
        pub_done_count = int((pub_status == pub_done).sum())
        obs_total = int(obs_mask.sum())
        general_metrics = {
            "total": total,
            "en_proceso": total - pub_done_count,
            "normalizadas": norm_ok_count,
            "con_observaciones": obs_total,
            "publicadas": pub_done_count,
            "avance": round((pub_done_count / total * 100) if total else 0, 2),
        }
        assignment_col = config.ASSIGNMENT_COLUMN
        distributed = (
            int(df[assignment_col].fillna("").astype(str).str.strip().ne("").sum())
            if assignment_col in df.columns
            else 0
        )
        pipeline = {
            "registradas": total,
            "distribuidas": distributed,
            "en_normalizacion": int((norm_status != norm_ok).sum()),
            "normalizadas": norm_ok_count,
            "en_publicacion": int(((norm_status == norm_ok) & (pub_status != pub_done)).sum()),
            "publicadas": pub_done_count,
        }
        reviewer_col = config.NORMALIZATION_REVIEWER_COLUMN
        norm_productivity = {}
        if reviewer_col in df.columns:
            norm_productivity = (
                df[df[reviewer_col].fillna("").astype(str).str.strip() != ""]
                .groupby(reviewer_col)
                .size()
                .sort_values(ascending=False)
                .to_dict()
            )
        publisher_col = config.PUBLICATION_PUBLISHED_BY_COLUMN
        pub_productivity = {}
        if publisher_col in df.columns:
            pub_productivity = (
                df[df[publisher_col].fillna("").astype(str).str.strip() != ""]
                .groupby(publisher_col)
                .size()
                .sort_values(ascending=False)
                .to_dict()
            )
        ranking = {}
        for person, count in norm_productivity.items():
            ranking[person] = ranking.get(person, 0) + int(count)
        for person, count in pub_productivity.items():
            ranking[person] = ranking.get(person, 0) + int(count)
        ranking = dict(sorted(ranking.items(), key=lambda kv: kv[1], reverse=True))
        obs_column = config.NORMALIZATION_OBS_COLUMN
        quality = {
            "observaciones": obs_total,
            "observaciones_por_responsable": (
                df[obs_mask]
                .groupby(reviewer_col)[obs_column]
                .count()
                .sort_values(ascending=False)
                .to_dict()
                if reviewer_col in df.columns and obs_column in df.columns
                else {}
            ),
            "retrabajos": int(((obs_mask) & (norm_status != norm_ok)).sum()),
        }
        time_metrics = {}
        if "Fecha" in df.columns:
            fecha = pd.to_datetime(df["Fecha"], errors="coerce")
            if config.NORMALIZATION_DATE_COLUMN in df.columns:
                t_norm = (pd.to_datetime(df[config.NORMALIZATION_DATE_COLUMN], errors="coerce") - fecha).dt.days.dropna()
                if not t_norm.empty:
                    time_metrics["registro_a_normalizacion"] = round(float(t_norm.mean()), 2)
            if config.PUBLICATION_DATE_COLUMN in df.columns:
                norm_date = pd.to_datetime(df.get(config.NORMALIZATION_DATE_COLUMN), errors="coerce")
                t_pub = (pd.to_datetime(df[config.PUBLICATION_DATE_COLUMN], errors="coerce") - norm_date).dt.days.dropna()
                if not t_pub.empty:
                    time_metrics["normalizacion_a_publicacion"] = round(float(t_pub.mean()), 2)
                t_total = (pd.to_datetime(df[config.PUBLICATION_DATE_COLUMN], errors="coerce") - fecha).dt.days.dropna()
                if not t_total.empty:
                    time_metrics["ciclo_total"] = round(float(t_total.mean()), 2)
        return {
            "general": general_metrics,
            "pipeline": pipeline,
            "productividad_normalizacion": norm_productivity,
            "productividad_publicacion": pub_productivity,
            "ranking": ranking,
            "calidad": quality,
            "tiempos": time_metrics,
        }

    def dashboard_stage_masks(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        norm_status, pub_status, obs_mask = self._dashboard_vectors(df)
        norm_ok = (config.NORMALIZATION_OK_VALUE or "OK").upper()
        pub_done = (config.PUBLICATION_DONE_VALUE or "PUBLICADO").upper()
        base_mask = pd.Series(True, index=df.index, dtype=bool)
        masks = {
            "Registradas": base_mask,
            "En proceso": pub_status != pub_done,
            "Normalizadas": norm_status == norm_ok,
            "Con observaciones": obs_mask,
            "Publicadas": pub_status == pub_done,
        }
        return masks
