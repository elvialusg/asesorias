"""Vistas principales usando Streamlit."""

from __future__ import annotations

import io
from datetime import date
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from asesorias_app.config import TEMPLATE_PATH
from asesorias_app.core import utils
from asesorias_app.services.registro_service import RegistroService
from asesorias_app.ui.theme import load_theme

STATUS_OPTIONS = ["SI", "NO", "EN PROCESO"]
STATUS_LABELS = {"SI": "Si", "NO": "No", "EN PROCESO": "En proceso"}
PAZ_OPTIONS = ["EN PROCESO", "SI", "NO"]
PAZ_LABELS = {"EN PROCESO": "En proceso", "SI": "Sí", "NO": "No"}


def _streamlit_rerun() -> None:
    """Compatibilidad entre st.rerun y experimental_rerun."""
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
    else:
        st.experimental_rerun()


def _select_with_display(label: str, options: List[str], display_map: Dict[str, str], key: str):
    return st.selectbox(label, options, format_func=lambda opt: display_map.get(opt, opt), key=key)


def _format_list_label(option) -> str:
    if option is None:
        return ""
    text = str(option)
    # Replace underscores with spaces and collapse duplicate spaces.
    cleaned = text.replace("_", " ").strip()
    return " ".join(cleaned.split()) if cleaned else ""


def _all_widget_keys() -> List[str]:
    base = [
        "facultad",
        "programa",
        "cedula",
        "nombre_usuario",
        "titulo",
        "fecha",
        "rev_inicial",
        "rev_plantilla",
        "ok_ref",
        "ok_serv",
        "esc_turnitin",
        "similitud",
        "aprob_sim",
        "obs",
        "paz_y_salvo",
    ]
    n = int(st.session_state.get("asesorias_n", 1))
    for i in range(n):
        base += [
            f"asesor_rec_{i}",
            f"nombre_asesoria_{i}",
            f"modalidad_{i}",
            f"asesor_metodologico_{i}",
            f"modalidad2_{i}",
        ]
    return base


def _reset_form(meta: dict) -> None:
    for key in _all_widget_keys():
        st.session_state.pop(key, None)

    st.session_state["asesorias_n"] = 1
    st.session_state["cedula"] = ""
    st.session_state["nombre_usuario"] = ""
    st.session_state["titulo"] = ""
    st.session_state["fecha"] = date.today()
    st.session_state["obs"] = ""
    st.session_state["similitud"] = 0
    st.session_state["paz_y_salvo"] = "EN PROCESO"
    st.session_state["ok_ref"] = "EN PROCESO"
    st.session_state["ok_serv"] = "EN PROCESO"

    fac_names = meta["df_fac"]["Nombre_Facultad"].dropna().astype(str).tolist()
    st.session_state["facultad"] = fac_names[0] if fac_names else ""
    if fac_names:
        df_fac = meta["df_fac"]
        df_prog = meta["df_prog"]
        fac_code = int(df_fac.loc[df_fac["Nombre_Facultad"] == fac_names[0], "Codigo_Facultad"].iloc[0])
        prog_field = "Código_Facultad" if "Código_Facultad" in df_prog.columns else "Códígo_Facultad"
        progs = df_prog.loc[df_prog[prog_field] == fac_code, "Nombre_Programa"].dropna().astype(str).tolist()
        st.session_state["programa"] = progs[0] if progs else ""
    else:
        st.session_state["programa"] = ""

    lists = meta["lists"]
    st.session_state["rev_inicial"] = (lists.get("Revisión Inicial") or [""])[0]
    rev_pl = lists.get("Revisión de Plantilla") or lists.get("Revisión plantilla") or [""]
    st.session_state["rev_plantilla"] = rev_pl[0] if rev_pl else ""
    st.session_state["esc_turnitin"] = (lists.get("Escaneado Turnitin") or [""])[0]
    st.session_state["aprob_sim"] = (lists.get("Aprobados PyS") or [""])[0]

    st.session_state["asesor_rec_0"] = (lists.get("Asesor_Recursos_Académicos") or [""])[0]
    st.session_state["nombre_asesoria_0"] = (lists.get("Nombre_Asesoría") or [""])[0]
    st.session_state["modalidad_0"] = (lists.get("Modalidad_Asesoría") or ["Virtual"])[0]
    st.session_state["asesor_metodologico_0"] = ""
    st.session_state["modalidad2_0"] = ""


def _ensure_dynamic_defaults(meta: dict) -> None:
    lists = meta["lists"]
    n = int(st.session_state.get("asesorias_n", 1))
    for i in range(n):
        st.session_state.setdefault(f"asesor_rec_{i}", (lists.get("Asesor_Recursos_Académicos") or [""])[0])
        st.session_state.setdefault(f"nombre_asesoria_{i}", (lists.get("Nombre_Asesoría") or [""])[0])
        st.session_state.setdefault(f"modalidad_{i}", (lists.get("Modalidad_Asesoría") or ["Virtual"])[0])
        st.session_state.setdefault(f"asesor_metodologico_{i}", "")
        st.session_state.setdefault(f"modalidad2_{i}", "")


def _add_asesoria():
    st.session_state["asesorias_n"] = int(st.session_state.get("asesorias_n", 1)) + 1


def _autofill_by_cedula(meta: dict, service: RegistroService):
    ced = st.session_state.get("cedula", "").strip()
    if not ced:
        return
    df = service.load_registro()
    idx = service.find_student_index(df, cedula=ced, nombre=None)
    if idx is None:
        return
    st.session_state["nombre_usuario"] = str(df.loc[idx, "Nombre_Usuario"] or "")
    st.session_state["titulo"] = str(df.loc[idx, "Título_Trabajo_Grado"] or "")
    st.session_state["paz_y_salvo"] = str(df.loc[idx, "Paz_y_Salvo"] or "EN PROCESO")

    fac_norm = str(df.loc[idx, "Nombre_Facultad"] or "").strip()
    fac_display = meta["fac_norm_map"].get(fac_norm)
    if fac_display:
        st.session_state["facultad"] = fac_display
        prog = str(df.loc[idx, "Nombre_Programa"] or "").strip()
        if prog:
            st.session_state["programa"] = prog


def _render_tabs(service: RegistroService, meta: dict) -> None:
    load_theme()

    if st.session_state.get("reset_pending", False) or "init_done" not in st.session_state:
        _reset_form(meta)
        st.session_state["init_done"] = True
        st.session_state["reset_pending"] = False

    _ensure_dynamic_defaults(meta)

    tabs = st.tabs(["✚ Registrar asesoría", "🔍 Consultar usuario", "📂 Carga masiva"])
    _tab_registro(tabs[0], service, meta)
    _tab_consulta(tabs[1], service)
    _tab_masivo(tabs[2], service)


def _tab_registro(tab, service: RegistroService, meta: dict):
    lists = meta["lists"]
    df_fac = meta["df_fac"]
    df_prog = meta["df_prog"]

    with tab:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        colA, colB = st.columns([1.15, 0.85], gap="large")
        with colA:
            st.subheader("Formulario de registro")
            fac_names = df_fac["Nombre_Facultad"].dropna().astype(str).tolist()
            fac_display = st.selectbox("Facultad", fac_names, index=0, key="facultad")
            fac_code = int(df_fac.loc[df_fac["Nombre_Facultad"] == fac_display, "Codigo_Facultad"].iloc[0])
            prog_field = "Código_Facultad" if "Código_Facultad" in df_prog.columns else "Códígo_Facultad"
            progs = df_prog.loc[df_prog[prog_field] == fac_code, "Nombre_Programa"].dropna().astype(str).tolist() or [""]
            prog_display = st.selectbox("Programa", progs, index=0, key="programa")
            c1, c2 = st.columns(2)
            with c1:
                st.text_input(
                    "Cédula",
                    placeholder="Ej: 1032331000",
                    key="cedula",
                    on_change=lambda: _autofill_by_cedula(meta, service),
                )
            with c2:
                st.text_input("Nombre del usuario", placeholder="Ej: Juan Pérez", key="nombre_usuario")
            titulo = st.text_input("Título trabajo de grado", key="titulo")
            fecha = st.date_input("Fecha", key="fecha", format="DD/MM/YYYY")

            st.markdown("### Asesorías a registrar")
            n = int(st.session_state.get("asesorias_n", 1))
            cadd, _ = st.columns([0.3, 0.7])
            with cadd:
                st.button("Agregar asesoría", on_click=_add_asesoria, key="btn_add_asesoria")

            asesorias_payload = []
            for i in range(n):
                with st.expander(f"Asesoría #{i + 1}", expanded=(i == 0)):
                    asesor_rec_i = st.selectbox(
                        "Asesor Recursos Académicos",
                        lists.get("Asesor_Recursos_Académicos", [""]),
                        format_func=_format_list_label,
                        key=f"asesor_rec_{i}",
                    )
                    nombre_asesoria_i = st.selectbox(
                        "Nombre de la asesoría",
                        lists.get("Nombre_Asesoría", [""]),
                        format_func=_format_list_label,
                        key=f"nombre_asesoria_{i}",
                    )
                    modalidad_i = st.selectbox(
                        "Modalidad",
                        lists.get("Modalidad_Asesoría", ["Virtual", "Presencial"]),
                        format_func=_format_list_label,
                        key=f"modalidad_{i}",
                    )
                    st.markdown("**Asesor metodológico**")
                    asesor_met_i = st.text_input(
                        "Asesor metodológico (digita el nombre)",
                        placeholder="Ej: Carlos Rodriguez",
                        key=f"asesor_metodologico_{i}",
                    )
                    modalidad2_i = st.selectbox(
                        "Modalidad asesoría ", ["", "Virtual", "Presencial"], key=f"modalidad2_{i}"
                    )
                    if asesor_met_i and modalidad2_i:
                        campo_h = f"{asesor_met_i.strip()}, {modalidad2_i}"
                    elif asesor_met_i:
                        campo_h = asesor_met_i.strip()
                    else:
                        campo_h = None
                    asesorias_payload.append(
                        {
                            "Asesor_Recursos_Académicos": utils.norm_str(asesor_rec_i),
                            "Nombre_Asesoría": utils.norm_str(nombre_asesoria_i),
                            "Modalidad del Programa": utils.norm_str(modalidad_i),
                            "Modalidad": utils.norm_str(modalidad_i),
                            "Asesor_Metodológico": utils.norm_str(asesor_met_i),
                            "Modalidad_Asesoría2": utils.norm_str(modalidad2_i),
                            "Detalle_Asesor_Metodologico": utils.norm_str(campo_h),
                            "Fecha": pd.to_datetime(fecha).strftime("%d-%m-%Y"),
                        }
                    )

            c3, c4 = st.columns(2)
            with c3:
                rev_inicial = st.selectbox(
                    "Revisión inicial",
                    lists.get("Revisión Inicial", [""]),
                    format_func=_format_list_label,
                    key="rev_inicial",
                )
                rev_pl_opts = lists.get("Revisión de Plantilla") or lists.get("Revisión plantilla") or [""]
                rev_plantilla = st.selectbox(
                    "Revisión plantilla", rev_pl_opts, format_func=_format_list_label, key="rev_plantilla"
                )
                esc_turnitin = st.selectbox(
                    "Escaneado Turnitin",
                    lists.get("Escaneado Turnitin", [""]),
                    format_func=_format_list_label,
                    key="esc_turnitin",
                )
            with c4:
                st.session_state.setdefault("ok_serv", "EN PROCESO")
                ok_serv = _select_with_display(
                    "OK de servicios",
                    STATUS_OPTIONS,
                    STATUS_LABELS,
                    key="ok_serv",
                )
                st.session_state.setdefault("ok_ref", "EN PROCESO")
                ok_ref = _select_with_display(
                    "OK revisión de plantilla",
                    STATUS_OPTIONS,
                    STATUS_LABELS,
                    key="ok_ref",
                )
                similitud = st.number_input("% similitud", min_value=0, max_value=100, step=1, key="similitud")

            aprob_sim = st.selectbox(
                "Aprobación similitud",
                lists.get("Aprobados PyS", [""]),
                format_func=_format_list_label,
                key="aprob_sim",
            )
            obs = st.text_area("Observaciones", height=120, key="obs")
            paz_y_salvo = _select_with_display(
                "Estudiante apto para paz y salvo",
                PAZ_OPTIONS,
                PAZ_LABELS,
                key="paz_y_salvo",
            )

            principal = asesorias_payload[0] if asesorias_payload else {}
            base_row = {
                "Nombre_Facultad": utils.normalize_fac_name(fac_display),
                "Nombre_Programa": prog_display,
                "Cédula": utils.norm_str(st.session_state.get("cedula")),
                "Nombre_Usuario": utils.norm_str(st.session_state.get("nombre_usuario")),
                "Asesor_Recursos_Académicos": principal.get("Asesor_Recursos_Académicos"),
                "Nombre_Asesoría": principal.get("Nombre_Asesoría"),
                "Modalidad del Programa": principal.get("Modalidad del Programa") or principal.get("Modalidad"),
                "Modalidad": principal.get("Modalidad"),
                "Asesor_Metodológico": principal.get("Asesor_Metodológico"),
                "Modalidad_Asesoría2": principal.get("Modalidad_Asesoría2"),
                "Detalle_Asesor_Metodologico": principal.get("Detalle_Asesor_Metodologico"),
                "Título_Trabajo_Grado": utils.norm_str(titulo),
                "Fecha": pd.to_datetime(fecha),
                "Revisión Inicial": utils.norm_str(rev_inicial),
                "Revisión plantilla": utils.norm_str(rev_plantilla),
                "Ok_Referencistas": utils.norm_str(ok_ref),
                "OK_Servicios": utils.norm_str(ok_serv),
                "Observaciones": utils.norm_str(obs),
                "Escaneado Turnitin": utils.norm_str(esc_turnitin),
                "% similitud": int(similitud),
                "Aprobación_Similitud": utils.norm_str(aprob_sim),
                "Paz_y_Salvo": utils.norm_str(paz_y_salvo) or "EN PROCESO",
            }

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Guardar registro", type="primary"):
                    if not base_row["Cédula"] and not base_row["Nombre_Usuario"]:
                        st.warning("Escribe al menos el nombre o la cédula.")
                    else:
                        try:
                            service.add_registro(base_row, asesorias_payload)
                            st.success("Registro guardado.")
                            st.session_state["reset_pending"] = True
                            _streamlit_rerun()
                        except ValueError as exc:
                            st.warning(str(exc))
            with col_btn2:
                if st.button("✏️ Modificar / Adicionar asesoría", type="secondary"):
                    if not base_row["Cédula"] and not base_row["Nombre_Usuario"]:
                        st.warning("Indica el nombre o la cédula para buscar el registro.")
                    else:
                        try:
                            service.update_registro(base_row, asesorias_payload)
                            st.success("Registro actualizado.")
                            st.session_state["reset_pending"] = True
                            _streamlit_rerun()
                        except ValueError as exc:
                            st.warning(str(exc))

        with colB:
            st.subheader("Vista rápida")
            df_latest = service.load_registro()
            st.caption("Últimos 15 registros")
            show = df_latest.copy()
            sort_col = "Fecha" if "Fecha" in show.columns else None
            drop_cols = []
            if "Fecha" in show.columns:
                show["_Fecha_sort"] = pd.to_datetime(show["Fecha"], errors="coerce")
                show["Fecha"] = show["_Fecha_sort"].dt.strftime("%d-%m-%Y")
                sort_col = "_Fecha_sort"
                drop_cols.append("_Fecha_sort")
            sorted_show = show
            if sort_col:
                sorted_show = sorted_show.sort_values(sort_col, ascending=False)
            sorted_show = sorted_show.head(15)
            if drop_cols:
                sorted_show = sorted_show.drop(columns=drop_cols)
            st.dataframe(sorted_show, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def _tab_consulta(tab, service: RegistroService):
    with tab:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Buscar usuario, ver total, borrar y descargar Excel")
        df_latest = service.load_registro()
        search_cols = st.columns([0.85, 0.15])
        with search_cols[0]:
            q = st.text_input("Buscar por nombre o cédula", placeholder="Ej: Valentina o 1032331000", key="q_search")
        with search_cols[1]:
            if st.button("🔍", key="btn_search_trigger", help="Ejecutar búsqueda"):
                st.session_state["q_search"] = q.strip()
                _streamlit_rerun()
        q = q.strip()
        if q:
            q_low = q.lower()

            def match_row(row):
                name = str(row.get("Nombre_Usuario", "")).lower()
                ced = str(row.get("Cédula", "")).lower()
                return q_low in name or q_low in ced

            filtered = df_latest[df_latest.apply(match_row, axis=1)].copy()
        else:
            filtered = df_latest.copy()

        st.write(f"Registros encontrados: **{len(filtered)}**")
        cols_show = [
            c
            for c in [
                "Nombre_Usuario",
                "Cédula",
                "Título_Trabajo_Grado",
                "Total_Asesorías",
                "Historial_Asesorías",
                "Historial_Asesor_Recursos",
                "Paz_y_Salvo",
                "Fecha",
            ]
            if c in filtered.columns
        ]
        sort_col = "Fecha" if "Fecha" in filtered.columns else None
        if "Fecha" in filtered.columns:
            filtered["_Fecha_sort"] = pd.to_datetime(filtered["Fecha"], errors="coerce")
            filtered["Fecha"] = filtered["_Fecha_sort"].dt.strftime("%d-%m-%Y")
            sort_col = "_Fecha_sort"
        if not filtered.empty:
            df_to_show = filtered
            if sort_col:
                df_to_show = df_to_show.sort_values(sort_col, ascending=False)
            if "_Fecha_sort" in df_to_show.columns:
                df_to_show = df_to_show.drop(columns="_Fecha_sort")
            st.dataframe(df_to_show[cols_show], use_container_width=True)
        else:
            st.info("No hay registros para mostrar.")

        st.divider()
        st.markdown("### 📌 Historial del estudiante")
        if len(filtered) == 0:
            st.info("Primero busca un estudiante para ver su historial.")
        else:
            options = []
            for idx, row in filtered.iterrows():
                label = f"{row.get('Nombre_Usuario','')} | {row.get('Cédula','')} | Total: {row.get('Total_Asesorías',0)}"
                options.append((int(idx), label))
            sel = st.selectbox("Selecciona el estudiante para ver el historial", options, format_func=lambda x: x[1])
            sel_idx = sel[0]
            row = df_latest.loc[sel_idx]

            cinfo1, cinfo2, cinfo3 = st.columns(3)
            with cinfo1:
                st.metric("Estudiante", str(row.get("Nombre_Usuario", "")))
                st.write(f"**Cédula:** {row.get('Cédula','')}")
            with cinfo2:
                st.metric("Total asesorías", int(row.get("Total_Asesorías", 0) or 0))
                st.write(f"**Paz y salvo:** {row.get('Paz_y_Salvo','')}")
            with cinfo3:
                st.write("**Título trabajo de grado:**")
                st.write(str(row.get("Título_Trabajo_Grado", "")))

            hist_df = service.history_table_from_row(row)
            st.dataframe(hist_df, use_container_width=True)

            st.markdown("### 🧹 Eliminar una asesoría del historial")
            if len(hist_df) == 0:
                st.info("Este estudiante no tiene asesorías registradas.")
            else:
                n_values = hist_df["N"].tolist()
                n_to_delete = st.selectbox("Selecciona el número de la asesoría a eliminar", n_values)
                sel_row = hist_df[hist_df["N"] == n_to_delete].iloc[0]
                st.write("Vas a eliminar:")
                st.write(f"- **Fecha:** {sel_row.get('Fecha','')}")
                st.write(f"- **Asesoría:** {sel_row.get('Asesoría','')}")
                st.write(f"- **Asesor Recursos:** {sel_row.get('Asesor Recursos','')}")
                st.write(f"- **Asesor Metodológico:** {sel_row.get('Asesor Metodológico','')}")
                confirm_one = st.checkbox("Confirmo eliminar SOLO esta asesoría del historial", key="confirm_delete_one")
                if st.button("Eliminar asesoría seleccionada", disabled=not confirm_one):
                    df_all = service.load_registro()
                    updated = service.delete_history_item(df_all.loc[sel_idx].copy(), int(n_to_delete) - 1)
                    df_all.loc[sel_idx] = updated
                    service.save_registro(df_all)
                    st.success("Asesoría eliminada.")
                    _streamlit_rerun()

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                hist_df.to_excel(writer, index=False, sheet_name="Historial")
            buffer.seek(0)
            st.download_button(
                "Descargar historial (Excel)",
                data=buffer.read(),
                file_name=f"historial_{str(row.get('Cédula','')).strip() or 'estudiante'}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.divider()
        st.markdown("### 🗑 Eliminar registro (estudiante)")
        if len(filtered) == 0:
            st.info("No hay registros para eliminar con el filtro actual.")
        else:
            options_del = []
            for idx, row in filtered.iterrows():
                label = f"[{idx}] {row.get('Nombre_Usuario','')} | {row.get('Cédula','')} | Total: {row.get('Total_Asesorías',0)}"
                options_del.append((int(idx), label))
            selected = st.selectbox(
                "Selecciona el estudiante (fila) a eliminar",
                options_del,
                format_func=lambda x: x[1],
                key="del_select",
            )
            idx_to_delete = selected[0]
            confirm = st.checkbox("Confirmo que deseo eliminar este registro", key="del_confirm")
            if st.button("Eliminar registro seleccionado", type="primary", disabled=not confirm):
                service.delete_registro(idx_to_delete)
                st.success("Registro eliminado correctamente.")
                _streamlit_rerun()

        st.divider()
        st.markdown("### ⬇️ Descargar Excel actual")
        st.download_button(
            label="Descargar registro (Excel)",
            data=service.download_bytes(),
            file_name="registro_asesorias_actual.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)


def _tab_masivo(tab, service: RegistroService):
    with tab:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Carga masiva (plantilla · subir · actualizar registros)")
        template_cols = service.load_registro().columns.tolist()
        st.markdown("**1) Descargar plantilla** (mismos campos del formulario + paz y salvo).")
        st.download_button(
            "Descargar plantilla para carga masiva",
            data=service.build_bulk_template(template_cols),
            file_name="plantilla_carga_masiva_asesorias.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("**2) Subir archivo diligenciado** (crea o modifica el registro del estudiante).")
        up = st.file_uploader("Sube el Excel", type=["xlsx"], key="up_bulk")
        if up is not None:
            try:
                df_up = pd.read_excel(up)
                st.write("Vista previa (primeras 10 filas):")
                st.dataframe(df_up.head(10), use_container_width=True)
                if st.button("Importar / Actualizar", type="primary", key="btn_bulk_import"):
                    service.bulk_import(df_up)
                    st.success("Importación completada.")
                    _streamlit_rerun()
            except Exception as exc:
                st.error(f"No se pudo leer/importar el archivo: {exc}")
        st.markdown("</div>", unsafe_allow_html=True)


def render_app():
    load_theme()
    service = RegistroService()
    if not TEMPLATE_PATH.exists():
        st.error(
            f"No encuentro el template en: {TEMPLATE_PATH}\n\nDebe existir: data/Control_Asesorias_Tesis_template.xlsm"
        )
        return
    meta = service.load_lists()
    _render_tabs(service, meta)
