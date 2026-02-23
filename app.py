"""Punto de entrada de la aplicación Streamlit."""

from __future__ import annotations

import streamlit as st

from asesorias_app.ui.app_shell import render_app

st.set_page_config(page_title="Tablero Asesorías (Tesis)", layout="wide")


def main():
    render_app()


if __name__ == "__main__":
    main()
