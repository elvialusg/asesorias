"""Servicio con la lógica de negocio de los registros."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

import pandas as pd

from ..constants import (
    BASE_COLUMNS,
    COL_ASESOR_METODOLOGICO_DETALLE,
    COL_ASESOR_RECURSOS,
    COL_CEDULA,
    COL_FECHA,
    COL_HISTORIAL_ASESORIAS,
    COL_HISTORIAL_ASESOR_METODOLOGICO,
    COL_HISTORIAL_ASESOR_RECURSOS,
    COL_HISTORIAL_FECHAS,
    COL_MODALIDAD_PROGRAMA,
    COL_NOMBRE_ASESORIA,
    COL_NOMBRE_USUARIO,
    COL_PAZ_Y_SALVO,
    COL_PORCENTAJE_SIMILITUD,
    COL_TOTAL_ASESORIAS,
)
from ..models import RegistroAsesoria
from ..repositories import RegistroRepository
from ..utils import append_pipe, ensure_date, join_hist, norm_str, safe_int, split_hist


class RegistroService:
    """Opera sobre el repositorio aplicando reglas del dominio."""

    def __init__(self, repository: Optional[RegistroRepository] = None):
        self.repository = repository or RegistroRepository()

    # ---------------------- Lecturas ----------------------
    def get_dataframe(self) -> pd.DataFrame:
        records = self.repository.list_all()
        rows = [self._entity_to_row(record) for record in records]
        df = pd.DataFrame(rows)
        if df.empty:
            columns = [col for col in BASE_COLUMNS.values() if col != "id"]
            return pd.DataFrame(columns=columns)
        df = df.set_index("id")
        return df

    def get_record_row(self, record_id: int) -> Optional[Dict]:
        record = self.repository.get_by_id(record_id)
        if not record:
            return None
        return self._entity_to_row(record)

    def find_student(self, cedula: Optional[str], nombre: Optional[str]) -> Optional[Dict]:
        record = self.repository.get_by_identifiers(cedula, nombre)
        if not record:
            return None
        return self._entity_to_row(record)

    # ---------------------- Escrituras ----------------------
    def create_registro(self, base_row: Dict, asesorias_payload: List[Dict]) -> RegistroAsesoria:
        payload = base_row.copy()
        hist = self._build_historial_payload(asesorias_payload, base_row.get(COL_FECHA))
        payload.update(hist)
        entity_payload = self._row_to_entity_payload(payload)
        return self.repository.create(entity_payload)

    def update_registro(
        self,
        record_id: int,
        base_row: Dict,
        asesorias_payload: List[Dict],
    ) -> Optional[RegistroAsesoria]:
        record = self.repository.get_by_id(record_id)
        if not record:
            return None

        updates = self._row_to_entity_payload(base_row)
        if asesorias_payload:
            hist = self._append_historial_payload(record, asesorias_payload, base_row.get(COL_FECHA))
            updates.update(hist)

        return self.repository.update(record_id, updates)

    def delete_registro(self, record_id: int) -> bool:
        return self.repository.delete(record_id)

    def delete_historial_item(self, record_id: int, position: int) -> bool:
        record = self.repository.get_by_id(record_id)
        if not record:
            return False

        ases = split_hist(record.historial_asesorias)
        fechas = split_hist(record.historial_fechas)
        rec = split_hist(record.historial_asesor_recursos)
        met = split_hist(record.historial_asesor_metodologico)
        max_len = max(len(ases), len(fechas), len(rec), len(met))

        if position < 0 or position >= max_len:
            return False

        if position < len(ases):
            ases.pop(position)
        if position < len(fechas):
            fechas.pop(position)
        if position < len(rec):
            rec.pop(position)
        if position < len(met):
            met.pop(position)

        updated_total = max(safe_int(record.total_asesorias) - 1, 0)
        updates = {
            "total_asesorias": updated_total,
            "historial_asesorias": join_hist(ases),
            "historial_fechas": join_hist(fechas),
            "historial_asesor_recursos": join_hist(rec),
            "historial_asesor_metodologico": join_hist(met),
        }

        if updated_total <= 0:
            updates.update(
                {
                    "nombre_asesoria": "",
                    "asesor_recursos_academicos": "",
                    "fecha": None,
                }
            )
        else:
            if ases:
                updates["nombre_asesoria"] = ases[0]
            if rec:
                updates["asesor_recursos_academicos"] = rec[0]
            if fechas:
                new_date = ensure_date(fechas[0])
                updates["fecha"] = new_date

        return self.repository.update(record_id, updates) is not None

    def bulk_import(self, df_upload: pd.DataFrame) -> None:
        df_upload = df_upload.copy()
        if COL_FECHA in df_upload.columns:
            df_upload[COL_FECHA] = pd.to_datetime(df_upload[COL_FECHA], errors="coerce")

        for _, row in df_upload.iterrows():
            cedula = norm_str(row.get(COL_CEDULA))
            nombre = norm_str(row.get(COL_NOMBRE_USUARIO))
            if not cedula and not nombre:
                continue

            base_row = self._extract_base_row(row)
            base_row[COL_PAZ_Y_SALVO] = base_row.get(COL_PAZ_Y_SALVO) or "EN PROCESO"
            asesor_info = {
                COL_ASESOR_RECURSOS: norm_str(row.get(COL_ASESOR_RECURSOS)),
                COL_NOMBRE_ASESORIA: norm_str(row.get(COL_NOMBRE_ASESORIA)),
                COL_MODALIDAD_PROGRAMA: norm_str(row.get(COL_MODALIDAD_PROGRAMA)),
                COL_ASESOR_METODOLOGICO_DETALLE: norm_str(row.get(COL_ASESOR_METODOLOGICO_DETALLE)),
            }
            payload = [asesor_info] if any(asesor_info.values()) else []

            match = self.repository.get_by_identifiers(cedula, nombre)
            if not match:
                self.create_registro(base_row, payload)
            else:
                self.update_registro(match.id, base_row, payload)

    # ---------------------- Helpers ----------------------
    def _extract_base_row(self, row: pd.Series) -> Dict:
        all_columns = set(list(BASE_COLUMNS.values())[1:])
        skip = {
            COL_TOTAL_ASESORIAS,
            COL_HISTORIAL_ASESORIAS,
            COL_HISTORIAL_ASESOR_RECURSOS,
            COL_HISTORIAL_ASESOR_METODOLOGICO,
            COL_HISTORIAL_FECHAS,
        }
        allowed = all_columns - skip
        data = {}
        for column in allowed:
            if column in row.index:
                data[column] = row.get(column)
        return data

    def _entity_to_row(self, record: RegistroAsesoria) -> Dict:
        row = {"id": record.id}
        for attr, column in list(BASE_COLUMNS.items())[1:]:
            value = getattr(record, attr)
            row[column] = value
        return row

    def _row_to_entity_payload(self, row: Dict) -> Dict:
        payload: Dict = {}
        for attr, column in list(BASE_COLUMNS.items())[1:]:
            if column not in row:
                continue
            value = row[column]
            if column == COL_FECHA:
                payload[attr] = ensure_date(value)
            elif column == COL_TOTAL_ASESORIAS:
                payload[attr] = safe_int(value, 0)
            elif column == COL_PORCENTAJE_SIMILITUD:
                payload[attr] = float(value) if value not in (None, "") else None
            else:
                payload[attr] = value
        return payload

    def _build_historial_payload(self, asesorias_payload: List[Dict], fecha_value) -> Dict:
        total = len(asesorias_payload)
        hist_asesorias = ""
        hist_rec = ""
        hist_met = ""
        hist_fechas = ""
        date_str = self._historial_date_str(fecha_value)

        for asesoria in asesorias_payload:
            hist_asesorias = append_pipe(hist_asesorias, asesoria.get(COL_NOMBRE_ASESORIA))
            hist_rec = append_pipe(hist_rec, asesoria.get(COL_ASESOR_RECURSOS))
            hist_met = append_pipe(hist_met, asesoria.get(COL_ASESOR_METODOLOGICO_DETALLE))
            fecha_item = asesoria.get(COL_FECHA)
            hist_fechas = append_pipe(hist_fechas, self._historial_date_str(fecha_item) or date_str)

        return {
            COL_TOTAL_ASESORIAS: total,
            COL_HISTORIAL_ASESORIAS: hist_asesorias,
            COL_HISTORIAL_ASESOR_RECURSOS: hist_rec,
            COL_HISTORIAL_ASESOR_METODOLOGICO: hist_met,
            COL_HISTORIAL_FECHAS: hist_fechas,
        }

    def _append_historial_payload(self, record: RegistroAsesoria, asesorias_payload: List[Dict], fecha_value) -> Dict:
        total = safe_int(record.total_asesorias) + len(asesorias_payload)
        hist_asesorias = record.historial_asesorias or ""
        hist_rec = record.historial_asesor_recursos or ""
        hist_met = record.historial_asesor_metodologico or ""
        hist_fechas = record.historial_fechas or ""
        default_date = self._historial_date_str(fecha_value) or self._historial_date_str(record.fecha)

        for asesoria in asesorias_payload:
            hist_asesorias = append_pipe(hist_asesorias, asesoria.get(COL_NOMBRE_ASESORIA))
            hist_rec = append_pipe(hist_rec, asesoria.get(COL_ASESOR_RECURSOS))
            hist_met = append_pipe(hist_met, asesoria.get(COL_ASESOR_METODOLOGICO_DETALLE))
            hist_fechas = append_pipe(hist_fechas, self._historial_date_str(asesoria.get(COL_FECHA)) or default_date)

        return {
            COL_TOTAL_ASESORIAS: total,
            COL_HISTORIAL_ASESORIAS: hist_asesorias,
            COL_HISTORIAL_ASESOR_RECURSOS: hist_rec,
            COL_HISTORIAL_ASESOR_METODOLOGICO: hist_met,
            COL_HISTORIAL_FECHAS: hist_fechas,
        }

    def _historial_date_str(self, value) -> str:
        dt = ensure_date(value)
        if not dt:
            return ""
        return dt.strftime("%Y-%m-%d")

    def history_table_from_row(self, row: pd.Series) -> pd.DataFrame:
        ases = split_hist(row.get(COL_HISTORIAL_ASESORIAS))
        fechas = split_hist(row.get(COL_HISTORIAL_FECHAS))
        rec = split_hist(row.get(COL_HISTORIAL_ASESOR_RECURSOS))
        met = split_hist(row.get(COL_HISTORIAL_ASESOR_METODOLOGICO))

        max_len = max(len(ases), len(fechas), len(rec), len(met), 0)
        data = []
        for i in range(max_len):
            data.append(
                {
                    "N": i + 1,
                    "Asesoria": ases[i] if i < len(ases) else "",
                    "Fecha": fechas[i] if i < len(fechas) else "",
                    "Asesor Recursos": rec[i] if i < len(rec) else "",
                    "Asesor Metodologico": met[i] if i < len(met) else "",
                }
            )
        return pd.DataFrame(data)
