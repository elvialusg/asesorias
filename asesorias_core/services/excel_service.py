"""Servicios auxiliares para exportar/importar Excel."""

from __future__ import annotations

import io
from typing import Iterable, List

import pandas as pd

from ..constants import EXTRA_COLUMNS, normalize_column_name


class ExcelService:
    """Centraliza operaciones con archivos Excel."""

    def dataframe_to_bytes(self, df: pd.DataFrame, sheet_name: str = "Registro") -> bytes:
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        bio.seek(0)
        return bio.read()

    def build_template(self, columns: Iterable[str]) -> bytes:
        cols = [c for c in columns if c not in EXTRA_COLUMNS]
        if "Paz_y_Salvo" not in cols:
            cols.append("Paz_y_Salvo")
        df = pd.DataFrame(columns=cols)
        return self.dataframe_to_bytes(df, sheet_name="Plantilla")

    def normalize_upload_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renombra columnas del archivo cargado al estándar interno."""
        rename_map = {col: normalize_column_name(col) for col in df.columns}
        return df.rename(columns=rename_map)
