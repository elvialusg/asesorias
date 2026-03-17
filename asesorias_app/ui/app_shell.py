"""Vistas principales usando Streamlit."""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from asesorias_app.config import TEMPLATE_PATH
from asesorias_app.core import utils
from asesorias_app.services.registro_service import RegistroService
from asesorias_app.ui.theme import load_theme

PLACEHOLDER_OPTION = "Seleccionar"
STATUS_OPTIONS = ["SI", "NO", "EN PROCESO"]
STATUS_OPTIONS_WITH_PLACEHOLDER = [PLACEHOLDER_OPTION] + STATUS_OPTIONS
STATUS_LABELS = {"SI": "Si", "NO": "No", "EN PROCESO": "En proceso"}
STATUS_LABELS_WITH_PLACEHOLDER = {PLACEHOLDER_OPTION: PLACEHOLDER_OPTION, **STATUS_LABELS}
PAZ_OPTIONS = ["EN PROCESO", "SI", "NO"]
PAZ_OPTIONS_WITH_PLACEHOLDER = [PLACEHOLDER_OPTION] + PAZ_OPTIONS
PAZ_LABELS = {"EN PROCESO": "En proceso", "SI": "Sí", "NO": "No"}
PAZ_LABELS_WITH_PLACEHOLDER = {PLACEHOLDER_OPTION: PLACEHOLDER_OPTION, **PAZ_LABELS}


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
    if option == PLACEHOLDER_OPTION:
        return PLACEHOLDER_OPTION
    text = str(option)
    # Replace underscores with spaces and collapse duplicate spaces.
    cleaned = text.replace("_", " ").strip()
    return " ".join(cleaned.split()) if cleaned else ""


def _selected_value(value: Optional[str]) -> str:
    if value in (None, "", PLACEHOLDER_OPTION):
        return ""
    return str(value)


def _extra_students_count() -> int:
    return int(st.session_state.get("extra_students_count", 0))


def _add_extra_student() -> None:
    st.session_state["extra_students_count"] = _extra_students_count() + 1


def _remove_extra_student(index: int) -> None:
    count = _extra_students_count()
    if index < 0 or index >= count:
        return
    for j in range(index, count - 1):
        st.session_state[f"extra_doc_{j}"] = st.session_state.get(f"extra_doc_{j + 1}", "")
        st.session_state[f"extra_name_{j}"] = st.session_state.get(f"extra_name_{j + 1}", "")
    st.session_state.pop(f"extra_doc_{count - 1}", None)
    st.session_state.pop(f"extra_name_{count - 1}", None)
    st.session_state["extra_students_count"] = max(count - 1, 0)


def _clean_str(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _set_select_state(key: str, value) -> None:
    st.session_state[key] = _clean_str(value) or PLACEHOLDER_OPTION


def _all_widget_keys() -> List[str]:
    base = [
        "facultad",
        "programa",
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
    base += ["cedula", "nombre_usuario"]
    extra_n = _extra_students_count()
    base.append("extra_students_count")
    for i in range(extra_n):
        base += [f"extra_doc_{i}", f"extra_name_{i}"]
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
    st.session_state["paz_y_salvo"] = PLACEHOLDER_OPTION
    st.session_state["ok_ref"] = PLACEHOLDER_OPTION
    st.session_state["ok_serv"] = PLACEHOLDER_OPTION

    st.session_state["facultad"] = PLACEHOLDER_OPTION
    st.session_state["programa"] = PLACEHOLDER_OPTION

    st.session_state["rev_inicial"] = PLACEHOLDER_OPTION
    st.session_state["rev_plantilla"] = PLACEHOLDER_OPTION
    st.session_state["esc_turnitin"] = PLACEHOLDER_OPTION
    st.session_state["aprob_sim"] = PLACEHOLDER_OPTION

    st.session_state["asesor_rec_0"] = PLACEHOLDER_OPTION
    st.session_state["nombre_asesoria_0"] = PLACEHOLDER_OPTION
    st.session_state["modalidad_0"] = PLACEHOLDER_OPTION
    st.session_state["asesor_metodologico_0"] = ""
    st.session_state["modalidad2_0"] = PLACEHOLDER_OPTION
    st.session_state["extra_students_count"] = 0


def _ensure_dynamic_defaults(meta: dict) -> None:
    lists = meta["lists"]
    n = int(st.session_state.get("asesorias_n", 1))
    for i in range(n):
        st.session_state.setdefault(f"asesor_rec_{i}", PLACEHOLDER_OPTION)
        st.session_state.setdefault(f"nombre_asesoria_{i}", PLACEHOLDER_OPTION)
        st.session_state.setdefault(f"modalidad_{i}", PLACEHOLDER_OPTION)
        st.session_state.setdefault(f"asesor_metodologico_{i}", "")
        st.session_state.setdefault(f"modalidad2_{i}", PLACEHOLDER_OPTION)
    extra_n = _extra_students_count()
    for i in range(extra_n):
        st.session_state.setdefault(f"extra_doc_{i}", "")
        st.session_state.setdefault(f"extra_name_{i}", "")


def _add_asesoria():
    st.session_state["asesorias_n"] = int(st.session_state.get("asesorias_n", 1)) + 1


def _autofill_by_cedula(
    meta: dict, service: RegistroService, doc_key: str = "cedula", name_key: str = "nombre_usuario"
):
    ced = st.session_state.get(doc_key, "").strip()
    if not ced:
        return
    df = service.load_registro()
    idx = service.find_student_index(df, cedula=ced, nombre=None)
    if idx is None:
        st.session_state["search_modal"] = {
            "message": "El usuario no se encuentra registrado, puede crearlo.",
            "success": False,
            "expires_at": datetime.utcnow().timestamp() + 10,
        }
        return
    row = df.loc[idx]
    doc_value = _clean_str(row.get("Cédula") or row.get("CǸdula") or ced)
    st.session_state[doc_key] = doc_value
    st.session_state[name_key] = _clean_str(row.get("Nombre_Usuario"))
    st.session_state["titulo"] = _clean_str(row.get("Título_Trabajo_Grado"))
    st.session_state["obs"] = _clean_str(row.get("Observaciones"))
    _set_select_state("paz_y_salvo", row.get("Paz_y_Salvo"))
    _set_select_state("rev_inicial", row.get("Revisión Inicial"))
    rev_pl_value = row.get("Revisión plantilla") or row.get("Revisión de Plantilla")
    _set_select_state("rev_plantilla", rev_pl_value)
    _set_select_state("ok_ref", row.get("Ok_Referencistas"))
    _set_select_state("ok_serv", row.get("OK_Servicios"))
    _set_select_state("esc_turnitin", row.get("Escaneado Turnitin"))
    _set_select_state("aprob_sim", row.get("Aprobación_Similitud"))

    similitud_val = row.get("% similitud")
    try:
        st.session_state["similitud"] = int(float(similitud_val))
    except (TypeError, ValueError):
        st.session_state["similitud"] = 0

    fecha_val = row.get("Fecha")
    if fecha_val is not None:
        try:
            fecha_dt = pd.to_datetime(fecha_val)
            if not pd.isna(fecha_dt):
                st.session_state["fecha"] = fecha_dt.date()
        except Exception:
            pass

    fac_norm = _clean_str(row.get("Nombre_Facultad"))
    fac_display = meta["fac_norm_map"].get(fac_norm)
    if fac_display:
        st.session_state["facultad"] = fac_display
    else:
        st.session_state["facultad"] = fac_norm or PLACEHOLDER_OPTION
    prog = _clean_str(row.get("Nombre_Programa"))
    st.session_state["programa"] = prog or PLACEHOLDER_OPTION

    st.session_state["search_modal"] = {
        "message": "El usuario ya se encuentra registrado.",
        "success": True,
        "expires_at": datetime.utcnow().timestamp() + 10,
    }


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
        spacer_left, colA, spacer_right = st.columns([0.15, 0.7, 0.15])
        with colA:
            st.subheader("Formulario de registro")
            modal_data = st.session_state.get("search_modal")
            if modal_data:
                expires_at = modal_data.get("expires_at")
                now_ts = datetime.utcnow().timestamp()
                if expires_at and now_ts >= expires_at:
                    st.session_state.pop("search_modal", None)
                else:
                    message = modal_data.get("message", "")
                    success = modal_data.get("success")
                    bg_color = "rgba(16, 185, 129, 0.6)" if success else "rgba(245, 158, 11, 0.7)"
                    border_color = "#16a34a" if success else "#f97316"
                    modal_id = f"search_modal_{int(expires_at or now_ts)}"
                    components.html(
                        f"""
<div id="{modal_id}" style="
    padding: 1rem 1.2rem;
    border-radius: 0.65rem;
    border: 1px solid {border_color};
    background-color: {bg_color};
    color: #ffffff;
    font-weight: 600;
    font-size: 1rem;
    letter-spacing: 0.01em;
    margin-bottom: 0.75rem;
">
    {message}
</div>
<script>
setTimeout(function(){{
    var el = document.getElementById("{modal_id}");
    if (el) {{
        el.style.display = "none";
    }}
}}, 10000);
</script>
""",
                        height=70,
                    )
            fac_names = df_fac["Nombre_Facultad"].dropna().astype(str).tolist()
            fac_options = [PLACEHOLDER_OPTION] + fac_names
            fac_display = st.selectbox("Facultad", fac_options, key="facultad")

            if fac_display == PLACEHOLDER_OPTION:
                progs = []
            else:
                fac_code = int(df_fac.loc[df_fac["Nombre_Facultad"] == fac_display, "Codigo_Facultad"].iloc[0])
                prog_field = "Código_Facultad" if "Código_Facultad" in df_prog.columns else "Códígo_Facultad"
                progs = (
                    df_prog.loc[df_prog[prog_field] == fac_code, "Nombre_Programa"].dropna().astype(str).tolist()
                )

            prog_options = [PLACEHOLDER_OPTION] + progs
            if st.session_state.get("programa") not in prog_options:
                st.session_state["programa"] = PLACEHOLDER_OPTION
            prog_display = st.selectbox("Programa", prog_options, key="programa")

            st.caption("Estudiantes adicionales (opcional)")
            st.button(
                "➕ Agregar estudiante",
                on_click=_add_extra_student,
                key="btn_add_extra_student",
                type="secondary",
            )
            extra_n = _extra_students_count()
            extra_inputs = []
            for i in range(extra_n):
                with st.expander(f"Estudiante adicional #{i + 1}", expanded=True):
                    col_extra, col_actions = st.columns([0.65, 0.35])
                    with col_extra:
                        extra_doc_input = st.text_input(
                            "Documento/Id",
                            key=f"extra_doc_{i}",
                            placeholder="Ej: 1032331000",
                        )
                        extra_name_input = st.text_input(
                            "Nombre y apellidos",
                            key=f"extra_name_{i}",
                            placeholder="Ej: Maria Gomez",
                        )
                        extra_inputs.append((extra_doc_input, extra_name_input))
                    with col_actions:
                        st.button(
                            "Buscar",
                            key=f"btn_buscar_extra_{i}",
                            type="secondary",
                            on_click=lambda idx=i: _autofill_by_cedula(
                                meta, service, doc_key=f"extra_doc_{idx}", name_key=f"extra_name_{idx}"
                            ),
                        )
                        st.button(
                            "Eliminar",
                            key=f"btn_remove_extra_{i}",
                            type="secondary",
                            on_click=lambda idx=i: _remove_extra_student(idx),
                        )

            c1, c2 = st.columns(2)
            with c1:
                input_col, btn_col = st.columns([0.7, 0.3])
                with input_col:
                    primary_doc_input = st.text_input("Documento/Id *", placeholder="Ej: 1032331000", key="cedula")
                with btn_col:
                    st.button(
                        "Buscar",
                        type="secondary",
                        key="btn_buscar_cedula",
                        on_click=lambda: _autofill_by_cedula(meta, service),
                    )
            with c2:
                primary_name_input = st.text_input(
                    "Nombre y apellidos *", placeholder="Ej: Juan Pérez", key="nombre_usuario"
                )
            titulo = st.text_input("Título trabajo de grado", key="titulo")
            fecha = st.date_input("Fecha", key="fecha", format="DD/MM/YYYY")

            asesorias_payload = []

            c3, c4 = st.columns(2)
            with c3:
                rev_inicial_opts = [PLACEHOLDER_OPTION] + list(lists.get("Revisión Inicial") or [])
                rev_inicial = st.selectbox(
                    "Revisión inicial",
                    rev_inicial_opts,
                    format_func=_format_list_label,
                    key="rev_inicial",
                )
                rev_pl_opts = list(lists.get("Revisión de Plantilla") or lists.get("Revisión plantilla") or [])
                rev_plantilla = st.selectbox(
                    "Revisión plantilla",
                    [PLACEHOLDER_OPTION] + rev_pl_opts,
                    format_func=_format_list_label,
                    key="rev_plantilla",
                )
                esc_turnitin_opts = [PLACEHOLDER_OPTION] + list(lists.get("Escaneado Turnitin") or [])
                esc_turnitin = st.selectbox(
                    "Escaneado Turnitin",
                    esc_turnitin_opts,
                    format_func=_format_list_label,
                    key="esc_turnitin",
                )
            with c4:
                st.session_state.setdefault("ok_serv", PLACEHOLDER_OPTION)
                ok_serv = _select_with_display(
                    "OK de servicios",
                    STATUS_OPTIONS_WITH_PLACEHOLDER,
                    STATUS_LABELS_WITH_PLACEHOLDER,
                    key="ok_serv",
                )
                st.session_state.setdefault("ok_ref", PLACEHOLDER_OPTION)
                ok_ref = _select_with_display(
                    "OK revisión de plantilla",
                    STATUS_OPTIONS_WITH_PLACEHOLDER,
                    STATUS_LABELS_WITH_PLACEHOLDER,
                    key="ok_ref",
                )
                similitud = st.number_input("% similitud", min_value=0, max_value=100, step=1, key="similitud")

            aprob_sim_opts = [PLACEHOLDER_OPTION] + list(lists.get("Aprobados PyS") or [])
            aprob_sim = st.selectbox(
                "Aprobación similitud",
                aprob_sim_opts,
                format_func=_format_list_label,
                key="aprob_sim",
            )
            obs = st.text_area("Observaciones", height=120, key="obs")
            st.session_state.setdefault("paz_y_salvo", PLACEHOLDER_OPTION)
            paz_y_salvo = _select_with_display(
                "Estudiante apto para paz y salvo",
                PAZ_OPTIONS_WITH_PLACEHOLDER,
                PAZ_LABELS_WITH_PLACEHOLDER,
                key="paz_y_salvo",
            )

            principal = asesorias_payload[0] if asesorias_payload else {}
            fac_value = _selected_value(fac_display)
            prog_value = _selected_value(prog_display)
            rev_inicial_value = _selected_value(rev_inicial)
            rev_plantilla_value = _selected_value(rev_plantilla)
            ok_ref_value = _selected_value(ok_ref)
            ok_serv_value = _selected_value(ok_serv)
            esc_turnitin_value = _selected_value(esc_turnitin)
            aprob_sim_value = _selected_value(aprob_sim)
            paz_y_salvo_value = _selected_value(paz_y_salvo)
            base_row_template = {
                "Nombre_Facultad": utils.normalize_fac_name(fac_value) if fac_value else "",
                "Nombre_Programa": prog_value,
                "Asesor_Recursos_Académicos": principal.get("Asesor_Recursos_Académicos"),
                "Nombre_Asesoría": principal.get("Nombre_Asesoría"),
                "Modalidad del Programa": principal.get("Modalidad del Programa") or principal.get("Modalidad"),
                "Modalidad": principal.get("Modalidad"),
                "Asesor_Metodológico": principal.get("Asesor_Metodológico"),
                "Modalidad_Asesoría2": principal.get("Modalidad_Asesoría2"),
                "Detalle_Asesor_Metodologico": principal.get("Detalle_Asesor_Metodologico"),
                "Título_Trabajo_Grado": utils.norm_str(titulo),
                "Fecha": pd.to_datetime(fecha),
                "Revisión Inicial": utils.norm_str(rev_inicial_value),
                "Revisión plantilla": utils.norm_str(rev_plantilla_value),
                "Ok_Referencistas": utils.norm_str(ok_ref_value),
                "OK_Servicios": utils.norm_str(ok_serv_value),
                "Observaciones": utils.norm_str(obs),
                "Escaneado Turnitin": utils.norm_str(esc_turnitin_value),
                "% similitud": int(similitud),
                "Aprobación_Similitud": utils.norm_str(aprob_sim_value),
                "Paz_y_Salvo": utils.norm_str(paz_y_salvo_value),
            }

            primary_doc_raw = (primary_doc_input or "").strip()
            primary_name_raw = (primary_name_input or "").strip()
            students_to_save = [
                (
                    "principal",
                    utils.norm_str(primary_doc_raw),
                    utils.norm_str(primary_name_raw),
                )
            ]
            for i, (doc_input, name_input) in enumerate(extra_inputs):
                doc_raw = (doc_input or "").strip()
                name_raw = (name_input or "").strip()
                doc_val = utils.norm_str(doc_raw)
                name_val = utils.norm_str(name_raw)
                if doc_val or name_val:
                    if not doc_raw or not name_raw:
                        st.warning(f"Completa documento y nombre para el estudiante adicional #{i + 1}.")
                        return
                    students_to_save.append((f"extra_{i}", doc_val, name_val))

            with st.container():
                if st.button("💾 Guardar registro", type="primary"):
                    first_doc = (primary_doc_raw or "").strip()
                    first_name = (primary_name_raw or "").strip()
                    if not first_doc:
                        st.warning("El campo Documento/Id es obligatorio.")
                    elif not first_name:
                        st.warning("El campo Nombre y apellidos es obligatorio.")
                    else:
                        successes = 0
                        errors = []
                        for _, doc_val, name_val in students_to_save:
                            if not doc_val and not name_val:
                                continue
                            row = base_row_template.copy()
                            row["Cédula"] = doc_val
                            row["Nombre_Usuario"] = name_val
                            try:
                                service.add_registro(row, asesorias_payload)
                                successes += 1
                            except ValueError as exc:
                                errors.append(f"{name_val or doc_val}: {exc}")
                        if successes:
                            st.success(f"Registro guardado para {successes} estudiante(s).")
                        for err in errors:
                            st.warning(err)
                        if successes and not errors:
                            st.session_state["reset_pending"] = True
                            _streamlit_rerun()



def _tab_consulta(tab, service: RegistroService):
    with tab:
        st.subheader("Buscar usuario, ver total, borrar y descargar Excel")
        df_latest = service.load_registro()
        search_cols = st.columns([0.85, 0.15])
        with search_cols[0]:
            q = st.text_input("Buscar por nombre o cédula", placeholder="Ej: Valentina o 1032331000", key="q_search")
        with search_cols[1]:
            st.button("🔍", key="btn_search_trigger", help="Ejecutar búsqueda")
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


def _tab_masivo(tab, service: RegistroService):
    with tab:
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
