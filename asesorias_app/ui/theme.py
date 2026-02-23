"""Funciones relacionadas con el tema y estilos."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from asesorias_app.config import THEME_CSS


def load_theme() -> None:
    css_path = Path(THEME_CSS)
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
