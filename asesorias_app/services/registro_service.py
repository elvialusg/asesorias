"""Servicio con la lógica de negocio del registro."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Dict, List, Optional

import pandas as pd

from asesorias_app import config
from asesorias_app.core.utils import (
    append_pipe,
    join_hist,
    norm_str,
    normalize_fac_name,
    safe_int,
    split_hist,
)
from asesorias_app.repositories.excel_repository import ExcelRepository, normalize_registro_df
from asesorias_app.repositories.google_sheets_repository import GoogleSheetsRepository


EXTRA_COLS = [
    "Total_Asesorías",
    "Historial_Asesorías",
    "Historial_Asesores",
    "Historial_Fechas",
    "Historial_Asesor_Recursos",
    "Historial_Asesor_Metodologico",
    "Paz_y_Salvo",
    "Paz_y_SSalvo",
]


def build_detalle_asesor(nombre: Optional[str], modalidad: Optional[str]) -> str:
    nombre_norm = norm_str(nombre)
    modalidad_norm = norm_str(modalidad)
    if nombre_norm and modalidad_norm:
        return f"{nombre_norm}, {modalidad_norm}"
    return nombre_norm or modalidad_norm or ""


class RegistroService:
    def __init__(self, repository: Optional[ExcelRepository] = None) -> None:
        if repository is not None:
            self.repo = repository
        elif config.GOOGLE_SHEETS_SPREADSHEET_ID:
            self.repo = GoogleSheetsRepository()
        else:
            self.repo = ExcelRepository()

    # Helpers --------------------------------------------------------------
    def load_lists(self):
        data = self.repo.load_lists()
        fac_names = data["df_fac"]["Nombre_Facultad"].dropna().astype(str).tolist()
        fac_norm_map = {normalize_fac_name(n): n for n in fac_names}
        data["fac_norm_map"] = fac_norm_map
        return data

    def load_registro(self) -> pd.DataFrame:
        df = self.repo.load_registro()
        for col in EXTRA_COLS:
            if col not in df.columns:
                df[col] = None
        if "Total_Asesorías" in df.columns:
            df["Total_Asesorías"] = pd.to_numeric(df["Total_Asesorías"], errors="coerce").fillna(0).astype(int)
        return df

    def save_registro(self, df: pd.DataFrame) -> None:
        self.repo.save_registro(df)

    def download_bytes(self) -> bytes:
        return self.repo.download_current_excel_bytes()

    def build_bulk_template(self, columns: List[str]) -> bytes:
        cols = [c for c in columns if c not in EXTRA_COLS]
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

        total = len(asesorias_payload)
        base_row["Total_Asesorías"] = total

        hist_asesorias = ""
        hist_rec = ""
        hist_met = ""
        hist_fechas = ""
        for asesoria in asesorias_payload:
            hist_asesorias = append_pipe(hist_asesorias, asesoria.get("Nombre_Asesoría"))
            hist_rec = append_pipe(hist_rec, asesoria.get("Asesor_Recursos_Académicos"))
            hist_met = append_pipe(hist_met, asesoria.get("Detalle_Asesor_Metodologico"))
            hist_fechas = append_pipe(hist_fechas, asesoria.get("Fecha"))

        base_row["Historial_Asesorías"] = hist_asesorias
        base_row["Historial_Asesor_Recursos"] = hist_rec
        base_row["Historial_Asesor_Metodologico"] = hist_met
        base_row["Historial_Asesores"] = hist_met
        base_row["Historial_Fechas"] = hist_fechas

        df_new = pd.concat([df_current, pd.DataFrame([base_row])], ignore_index=True)
        self.save_registro(df_new)

    def update_registro(self, base_row: Dict, asesorias_payload: List[Dict]) -> None:
        df_current = self.load_registro()
        idx = self.find_student_index(df_current, base_row.get("Cédula"), base_row.get("Nombre_Usuario"))
        if idx is None:
            raise ValueError("El estudiante no existe.")

        for key, value in base_row.items():
            if key in df_current.columns and norm_str(value) is not None:
                df_current.loc[idx, key] = value

        add_count = len(asesorias_payload)
        df_current.loc[idx, "Total_Asesorías"] = safe_int(df_current.loc[idx, "Total_Asesorías"]) + add_count

        for asesoria in asesorias_payload:
            df_current.loc[idx, "Historial_Asesorías"] = append_pipe(
                df_current.loc[idx, "Historial_Asesorías"], asesoria.get("Nombre_Asesoría")
            )
            df_current.loc[idx, "Historial_Asesor_Recursos"] = append_pipe(
                df_current.loc[idx, "Historial_Asesor_Recursos"], asesoria.get("Asesor_Recursos_Académicos")
            )
            df_current.loc[idx, "Historial_Asesor_Metodologico"] = append_pipe(
                df_current.loc[idx, "Historial_Asesor_Metodologico"], asesoria.get("Detalle_Asesor_Metodologico")
            )
            df_current.loc[idx, "Historial_Asesores"] = df_current.loc[idx, "Historial_Asesor_Metodologico"]
            df_current.loc[idx, "Historial_Fechas"] = append_pipe(
                df_current.loc[idx, "Historial_Fechas"], asesoria.get("Fecha")
            )

        self.save_registro(df_current)

    def delete_registro(self, index_to_delete: int) -> None:
        df = self.load_registro()
        df = df.drop(index=index_to_delete).reset_index(drop=True)
        self.save_registro(df)

    def delete_history_item(self, row: pd.Series, pos: int) -> pd.Series:
        ases = split_hist(row.get("Historial_Asesorías"))
        fechas = split_hist(row.get("Historial_Fechas"))
        rec = split_hist(row.get("Historial_Asesor_Recursos"))
        met = split_hist(row.get("Historial_Asesor_Metodologico"))
        max_len = max(len(ases), len(fechas), len(rec), len(met))
        if pos < 0 or pos >= max_len:
            return row

        if pos < len(ases):
            ases.pop(pos)
        if pos < len(fechas):
            fechas.pop(pos)
        if pos < len(rec):
            rec.pop(pos)
        if pos < len(met):
            met.pop(pos)

        row["Historial_Asesorías"] = join_hist(ases)
        row["Historial_Fechas"] = join_hist(fechas)
        row["Historial_Asesor_Recursos"] = join_hist(rec)
        row["Historial_Asesor_Metodologico"] = join_hist(met)
        row["Historial_Asesores"] = row["Historial_Asesor_Metodologico"]

        total = safe_int(row.get("Total_Asesorías", 0))
        row["Total_Asesorías"] = max(total - 1, 0)
        if row["Total_Asesorías"] <= 0:
            row["Nombre_Asesoría"] = ""
            row["Asesor_Recursos_Académicos"] = ""
            row["Fecha"] = pd.NaT
        else:
            if ases:
                row["Nombre_Asesoría"] = ases[0]
            if rec:
                row["Asesor_Recursos_Académicos"] = rec[0]
            if fechas:
                row["Fecha"] = pd.to_datetime(fechas[0], errors="coerce", dayfirst=True)
        return row

    def history_table_from_row(self, row: pd.Series) -> pd.DataFrame:
        ases = split_hist(row.get("Historial_Asesorías"))
        fechas = split_hist(row.get("Historial_Fechas"))
        rec = split_hist(row.get("Historial_Asesor_Recursos"))
        met = split_hist(row.get("Historial_Asesor_Metodologico"))
        fechas_fmt: List[str] = []
        for value in fechas:
            parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
            if pd.isna(parsed):
                fechas_fmt.append(value or "")
            else:
                fechas_fmt.append(parsed.strftime("%d-%m-%Y"))
        max_len = max(len(ases), len(fechas), len(rec), len(met))
        data = []
        for idx in range(max_len):
            data.append(
                {
                    "N": idx + 1,
                    "Asesoría": ases[idx] if idx < len(ases) else "",
                    "Fecha": fechas_fmt[idx] if idx < len(fechas_fmt) else "",
                    "Asesor Recursos": rec[idx] if idx < len(rec) else "",
                    "Asesor Metodológico": met[idx] if idx < len(met) else "",
                }
            )
        return pd.DataFrame(data)

    def bulk_import(self, df_upload: pd.DataFrame) -> None:
        df_upload = normalize_registro_df(df_upload.copy())
        if "Fecha" in df_upload.columns:
            df_upload["Fecha"] = pd.to_datetime(df_upload["Fecha"], errors="coerce").dt.strftime("%d-%m-%Y")

        df = self.load_registro()
        for _, row in df_upload.iterrows():
            ced = norm_str(row.get("Cédula"))
            nom = norm_str(row.get("Nombre_Usuario"))
            if not ced and not nom:
                continue

            base_row = {}
            for col in df.columns:
                if col in EXTRA_COLS:
                    continue
                if col in row.index:
                    base_row[col] = row.get(col)

            base_row["Paz_y_Salvo"] = norm_str(row.get("Paz_y_Salvo")) or "EN PROCESO"
            fecha_val = pd.to_datetime(row.get("Fecha"), errors="coerce")
            if pd.isna(fecha_val):
                fecha_val = pd.Timestamp(date.today())
            base_row["Fecha"] = fecha_val

            detalle = build_detalle_asesor(row.get("Asesor_Metodológico"), row.get("Modalidad_Asesoría2"))
            asesoria_payload = [
                {
                    "Nombre_Asesoría": norm_str(row.get("Nombre_Asesoría")),
                    "Asesor_Recursos_Académicos": norm_str(row.get("Asesor_Recursos_Académicos")),
                    "Detalle_Asesor_Metodologico": detalle,
                    "Fecha": base_row["Fecha"].strftime("%d-%m-%Y")
                    if pd.notna(base_row["Fecha"])
                    else date.today().strftime("%d-%m-%Y"),
                }
            ]

            idx = self.find_student_index(df, ced, nom)
            if idx is None:
                base_row["Total_Asesorías"] = 1
                base_row["Historial_Asesorías"] = asesoria_payload[0]["Nombre_Asesoría"] or ""
                base_row["Historial_Fechas"] = asesoria_payload[0]["Fecha"]
                base_row["Historial_Asesor_Recursos"] = asesoria_payload[0]["Asesor_Recursos_Académicos"] or ""
                base_row["Historial_Asesor_Metodologico"] = detalle or ""
                base_row["Historial_Asesores"] = base_row["Historial_Asesor_Metodologico"]
                df = pd.concat([df, pd.DataFrame([base_row])], ignore_index=True)
            else:
                for key, value in base_row.items():
                    if key in df.columns and norm_str(value) is not None:
                        df.loc[idx, key] = value
                df.loc[idx, "Total_Asesorías"] = safe_int(df.loc[idx, "Total_Asesorías"]) + 1
                df.loc[idx, "Historial_Asesorías"] = append_pipe(
                    df.loc[idx, "Historial_Asesorías"], asesoria_payload[0]["Nombre_Asesoría"]
                )
                df.loc[idx, "Historial_Asesor_Recursos"] = append_pipe(
                    df.loc[idx, "Historial_Asesor_Recursos"], asesoria_payload[0]["Asesor_Recursos_Académicos"]
                )
                df.loc[idx, "Historial_Asesor_Metodologico"] = append_pipe(
                    df.loc[idx, "Historial_Asesor_Metodologico"], detalle
                )
                df.loc[idx, "Historial_Asesores"] = df.loc[idx, "Historial_Asesor_Metodologico"]
                df.loc[idx, "Historial_Fechas"] = append_pipe(
                    df.loc[idx, "Historial_Fechas"], asesoria_payload[0]["Fecha"]
                )

        self.save_registro(df)
