"""Vistas principales usando Streamlit."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional
import io

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from asesorias_app import config
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
HIDDEN_COLUMNS = {"Asesor_Recursos_Académicos", "Nombre_Asesoría", "Asesor_Metodológico"}

DASHBOARD_BG_COLOR = "#f4fbf5"
DASHBOARD_TEXT_COLOR = "#0d1f17"
DASHBOARD_GREEN_PALETTE = ["#186f65", "#2f8f83", "#48b19b", "#73d6b8", "#a3e6c9", "#d6f7e7"]
BUTTON_STYLE_STATE_KEY = "_button_styles_applied"
ADD_BUTTON_STYLE_STATE_KEY = "_add_student_button_style"


def _style_dashboard_chart(chart):
    return (
        chart
        .configure_title(color=DASHBOARD_TEXT_COLOR, fontSize=16, anchor="start")
        .configure_axis(labelColor=DASHBOARD_TEXT_COLOR, titleColor=DASHBOARD_TEXT_COLOR, gridColor="#b7e4c7")
        .configure_legend(labelColor=DASHBOARD_TEXT_COLOR, titleColor=DASHBOARD_TEXT_COLOR)
        .configure_view(strokeWidth=0, fill=DASHBOARD_BG_COLOR)
        .interactive()
    )


def _inject_button_styles() -> None:
    if st.session_state.get(BUTTON_STYLE_STATE_KEY):
        return
    st.session_state[BUTTON_STYLE_STATE_KEY] = True
    primary_bg = DASHBOARD_GREEN_PALETTE[0]
    primary_hover = "#14594f"
    secondary_border = DASHBOARD_GREEN_PALETTE[0]
    st.markdown(
        f"""
<style>
div[data-testid="baseButton-primary"] button {{
    background-color: {primary_bg};
    color: #ffffff;
    border-radius: 999px;
    border: 1px solid {primary_bg};
    padding: 0.45rem 1.5rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}}
div[data-testid="baseButton-primary"] button:hover {{
    background-color: {primary_hover};
    border-color: {primary_hover};
}}
div[data-testid="baseButton-secondary"] button {{
    background-color: transparent;
    color: {DASHBOARD_TEXT_COLOR};
    border-radius: 999px;
    border: 1px solid {secondary_border};
    padding: 0.4rem 1.25rem;
    font-weight: 500;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}}
div[data-testid="baseButton-secondary"] button:hover {{
    background-color: #e2f5ec;
    border-color: {primary_bg};
}}
div[data-testid="baseButton-primary"] button:focus,
div[data-testid="baseButton-secondary"] button:focus {{
    outline: none;
    box-shadow: 0 0 0 2px rgba(24, 111, 101, 0.35);
}}
div[data-testid="baseButton-primary"] button:disabled,
div[data-testid="baseButton-secondary"] button:disabled {{
    opacity: 0.55;
    cursor: not-allowed;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _button(label: str, **kwargs):
    _inject_button_styles()
    clean_label = utils.fix_text_encoding(label, strip=True) or ""
    return st.button(clean_label, **kwargs)


def _inject_add_student_button_style() -> None:
    if st.session_state.get(ADD_BUTTON_STYLE_STATE_KEY):
        return
    st.session_state[ADD_BUTTON_STYLE_STATE_KEY] = True
    st.markdown(
        """
<style>
div[data-testid="baseButton-secondary"][id*="btn_add_extra_student"] button {
    width: 2.5rem;
    height: 2.5rem;
    padding: 0 !important;
    font-size: 1.6rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.75rem;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _download_label_for_responsable(responsable: Optional[str], *, show_all: bool = False, context: str) -> str:
    clean_responsable = utils.fix_text_encoding(responsable, strip=True) if responsable else responsable
    primary = utils.fix_text_encoding(config.PUBLICATION_PRIMARY, strip=True)
    secondary = (
        utils.fix_text_encoding(config.PUBLICATION_RESPONSIBLES[1], strip=True)
        if len(config.PUBLICATION_RESPONSIBLES) > 1
        else None
    )
    if context == "publicacion":
        if show_all:
            return "Descargar registros de todos"
        if clean_responsable == primary:
            return "Descargar registros"
        if clean_responsable == secondary:
            return "Descargar registros asignados"
    if clean_responsable:
        return f"Descargar registros de {clean_responsable}"
    return "Descargar registros"


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
        st.session_state[f"extra_email_{j}"] = st.session_state.get(f"extra_email_{j + 1}", "")
    st.session_state.pop(f"extra_doc_{count - 1}", None)
    st.session_state.pop(f"extra_name_{count - 1}", None)
    st.session_state.pop(f"extra_email_{count - 1}", None)
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
        "correo",
        "asesor_met_general",
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
            f"asesor_metodologico_{i}",
        ]
    base += ["cedula", "nombre_usuario"]
    extra_n = _extra_students_count()
    base.append("extra_students_count")
    for i in range(extra_n):
        base += [f"extra_doc_{i}", f"extra_name_{i}", f"extra_email_{i}"]
    return base


def _reset_form(meta: dict) -> None:
    for key in _all_widget_keys():
        st.session_state.pop(key, None)

    st.session_state["asesorias_n"] = 1
    st.session_state["cedula"] = ""
    st.session_state["nombre_usuario"] = ""
    st.session_state["correo"] = ""
    st.session_state["asesor_met_general"] = ""
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
    st.session_state["asesor_metodologico_0"] = ""
    st.session_state["extra_students_count"] = 0


def _ensure_dynamic_defaults(meta: dict) -> None:
    lists = meta["lists"]
    n = int(st.session_state.get("asesorias_n", 1))
    for i in range(n):
        st.session_state.setdefault(f"asesor_rec_{i}", PLACEHOLDER_OPTION)
        st.session_state.setdefault(f"nombre_asesoria_{i}", PLACEHOLDER_OPTION)
        st.session_state.setdefault(f"asesor_metodologico_{i}", "")
    extra_n = _extra_students_count()
    for i in range(extra_n):
        st.session_state.setdefault(f"extra_doc_{i}", "")
        st.session_state.setdefault(f"extra_name_{i}", "")
        st.session_state.setdefault(f"extra_email_{i}", "")


def _add_asesoria():
    st.session_state["asesorias_n"] = int(st.session_state.get("asesorias_n", 1)) + 1


def _autofill_by_cedula(
    meta: dict,
    service: RegistroService,
    doc_key: str = "cedula",
    name_key: str = "nombre_usuario",
    show_modal: bool = True,
):
    ced = st.session_state.get(doc_key, "").strip()
    if not ced:
        return
    df = service.load_registro()
    idx = service.find_student_index(df, cedula=ced, nombre=None)
    if idx is None:
        if show_modal:
            st.session_state["search_modal"] = {
                "message": "El usuario no se encuentra registrado, puede crearlo.",
                "success": False,
                "expires_at": datetime.utcnow().timestamp() + 10,
            }
        return
    row = df.loc[idx]
    doc_value = _clean_str(row.get("Cédula") or row.get("C?dula") or ced)
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

    if show_modal:
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

    st.markdown(
        """
<div style="
    background-color: #0f172a;
    color: #f8fafc;
    padding: 1rem 1.5rem;
    border-radius: 0.6rem;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: 0.015em;
    text-align: center;
    margin-bottom: 1rem;
">
    Registro y seguimiento de tesis
</div>
""",
        unsafe_allow_html=True,
    )

    menu_col, content_col = st.columns([0.24, 0.76])
    menu_items = {
        "register": "Registrar tesis",
        "consult": "Consultar usuario",
        "normalizacion": "Normalización",
        "publicacion": "Publicación",
        "dashboard": "Metricas",
    }
    query_params = st.query_params
    current_page = query_params.get("page", "register")
    if isinstance(current_page, list):
        current_page = current_page[0] if current_page else "register"
    if current_page not in menu_items:
        current_page = "register"
    st.session_state["current_page"] = current_page

    with menu_col:
        with st.expander("Menú", expanded=True):
            st.markdown(
                """
<style>
a.menu-link {
    color: #f8fafc;
    text-decoration: none;
    display: block;
    padding: 0.3rem 0;
    font-weight: 600;
}
a.menu-link.active {
    color: #0f172a;
    border-bottom: 2px solid #c8f560;
    padding-left: 0;
}
</style>
""",
                unsafe_allow_html=True,
            )
            for key, label in menu_items.items():
                is_active = st.session_state.get("current_page") == key
                href = f"?page={key}"
                classes = "menu-link active" if is_active else "menu-link"
                st.markdown(f'<a class="{classes}" href="{href}" target="_self">{label}</a>', unsafe_allow_html=True)

    with content_col:
        current = st.session_state.get("current_page", "register")
        if current == "register":
            _tab_registro(content_col, service, meta)
        elif current == "consult":
            _tab_consulta(content_col, service, meta)
        elif current == "normalizacion":
            _tab_normalizacion(content_col, service, meta)
        elif current == "publicacion":
            _tab_publicacion(content_col, service, meta)
        elif current == "dashboard":
            _tab_dashboard(content_col, service, meta)


def _tab_registro(tab, service: RegistroService, meta: dict):
    lists = meta["lists"]
    df_fac = meta["df_fac"]
    df_prog = meta["df_prog"]

    with tab:
        spacer_left, colA, spacer_right = st.columns([0.15, 0.7, 0.15])
        with colA:
            pending_doc = st.session_state.pop("pending_prefill_doc", None)
            if pending_doc:
                st.session_state["cedula"] = pending_doc
                _autofill_by_cedula(meta, service, doc_key="cedula", name_key="nombre_usuario", show_modal=False)
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
                    text_color = "#ffffff" if success else "#1f2937"
                    modal_id = f"search_modal_{int(expires_at or now_ts)}"
                    components.html(
                        f"""
<div id="{modal_id}" style="
    padding: 1rem 1.2rem;
    border-radius: 0.65rem;
    border: 1px solid {border_color};
    background-color: {bg_color};
    color: {text_color};
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
            editing_target = st.session_state.get("editing_target")
            if editing_target:
                edit_name = editing_target.get("nombre") or editing_target.get("cedula", "")
                st.info(f"Editando registro existente: {edit_name}. Guarda los cambios para actualizarlo.")
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
            modalidad_programa = st.selectbox(
                "Modalidad del programa",
                [PLACEHOLDER_OPTION, "Virtual", "Presencial"],
                key="modalidad_programa",
            )

            st.caption("Estudiantes adicionales (opcional)")
            btn_add_col, label_add_col = st.columns([0.15, 0.85])
            with btn_add_col:
                _button("+", on_click=_add_extra_student, key="btn_add_extra_student", type="secondary")
                _inject_add_student_button_style()
            with label_add_col:
                st.caption("Agregar estudiante adicional")
            extra_n = _extra_students_count()
            extra_inputs = []
            for i in range(extra_n):
                with st.expander(f"Estudiante adicional #{i + 1}", expanded=True):
                    col_extra, col_actions = st.columns([0.78, 0.22])
                    with col_extra:
                        extra_doc_input = st.text_input(
                            "Documento/Id",
                            key=f"extra_doc_{i}",
                            placeholder="Ej: 1032331000",
                            on_change=lambda idx=i: _autofill_by_cedula(
                                meta, service, doc_key=f"extra_doc_{idx}", name_key=f"extra_name_{idx}", show_modal=False
                            ),
                        )
                        extra_name_input = st.text_input(
                            "Nombre y apellidos",
                            key=f"extra_name_{i}",
                            placeholder="Ej: Maria Gomez",
                        )
                        extra_email_input = st.text_input(
                            "Correo electrónico",
                            key=f"extra_email_{i}",
                            placeholder="Ej: usuario@uni.edu",
                        )
                        extra_inputs.append((extra_doc_input, extra_name_input, extra_email_input))
                    with col_actions:
                        _button(
                            "Eliminar",
                            key=f"btn_remove_extra_{i}",
                            type="secondary",
                            on_click=lambda idx=i: _remove_extra_student(idx),
                        )

            c1, c2 = st.columns(2)
            with c1:
                primary_doc_input = st.text_input(
                    "Documento/Id *",
                    placeholder="Ej: 1032331000",
                    key="cedula",
                    on_change=lambda: _autofill_by_cedula(meta, service),
                )
            with c2:
                primary_name_input = st.text_input(
                    "Nombre y apellidos *", placeholder="Ej: Juan Pérez", key="nombre_usuario"
                )
            correo = st.text_input("Correo electrónico *", placeholder="Ej: usuario@uni.edu", key="correo")
            asesor_met_general = st.text_input("Asesor metodológico", key="asesor_met_general")
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
                "Modalidad del Programa": utils.norm_str(modalidad_programa),
                "Correo_Electronico": utils.norm_str(correo),
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
            primary_email_raw = (correo or "").strip()
            students_to_save = [
                (
                    "principal",
                    utils.norm_str(primary_doc_raw),
                    utils.norm_str(primary_name_raw),
                    utils.norm_str(primary_email_raw),
                )
            ]
            for i, (doc_input, name_input, email_input) in enumerate(extra_inputs):
                doc_raw = (doc_input or "").strip()
                name_raw = (name_input or "").strip()
                email_raw = (email_input or "").strip()
                doc_val = utils.norm_str(doc_raw)
                name_val = utils.norm_str(name_raw)
                email_val = utils.norm_str(email_raw)
                if doc_val or name_val or email_val:
                    if not doc_raw or not name_raw:
                        st.warning(f"Completa documento y nombre para el estudiante adicional #{i + 1}.")
                        return
                    if not email_raw:
                        st.warning(f"Completa el correo electrónico para el estudiante adicional #{i + 1}.")
                        return
                    students_to_save.append((f"extra_{i}", doc_val, name_val, email_val))

            with st.container():
                saving = st.session_state.get("saving", False)
                if saving:
                    st.info("Guardando registro...")
                if _button("Guardar registro", type="primary", disabled=saving):
                    first_doc = (primary_doc_raw or "").strip()
                    first_name = (primary_name_raw or "").strip()
                    first_email = (primary_email_raw or "").strip()
                    if not first_doc:
                        st.warning("El campo Documento/Id es obligatorio.")
                    elif not first_name:
                        st.warning("El campo Nombre y apellidos es obligatorio.")
                    elif not first_email:
                        st.warning("El campo Correo electr\xf3nico es obligatorio.")
                    else:
                        st.session_state["saving"] = True
                        successes = 0
                        errors = []
                        is_editing = bool(st.session_state.get("editing_target"))
                        with st.spinner("Guardando registro..."):
                            if is_editing:
                                row = base_row_template.copy()
                                row["C\xe9dula"] = utils.norm_str(primary_doc_raw)
                                row["Nombre_Usuario"] = utils.norm_str(primary_name_raw)
                                row["Correo_Electronico"] = utils.norm_str(primary_email_raw)
                                try:
                                    service.update_registro(row, asesorias_payload)
                                    successes = 1
                                except ValueError as exc:
                                    errors.append(str(exc))
                            else:
                                for _, doc_val, name_val, email_val in students_to_save:
                                    if not doc_val and not name_val:
                                        continue
                                    row = base_row_template.copy()
                                    row["C\xe9dula"] = doc_val
                                    row["Nombre_Usuario"] = name_val
                                    row["Correo_Electronico"] = email_val
                                    try:
                                        service.add_registro(row, asesorias_payload)
                                        successes += 1
                                    except ValueError as exc:
                                        errors.append(f"{name_val or doc_val}: {exc}")
                        st.session_state["saving"] = False
                        if successes:
                            success_message = (
                                "Registro actualizado correctamente."
                                if is_editing
                                else "Registro guardado."
                            )
                            st.markdown(
                                f"""
<div style="
    border-radius: 0.5rem;
    border: 1px solid #15803d;
    background-color: #16a34a;
    color: #ffffff;
    font-weight: 600;
    padding: 0.75rem 1rem;
    margin-top: 0.75rem;
">
    {success_message}
</div>
""",
                                unsafe_allow_html=True,
                            )
                        for err in errors:
                            st.warning(err)
                        if successes and not errors:
                            if is_editing:
                                st.session_state.pop("editing_target", None)
                            st.session_state["reset_pending"] = True
                            _streamlit_rerun()



def _tab_consulta(tab, service: RegistroService, meta: dict):
    with tab:
        try:
            df_latest = service.load_registro()
        except RuntimeError as exc:
            st.error(str(exc))
            return
        search_cols = st.columns([0.85, 0.15])
        with search_cols[0]:
            q = st.text_input("Buscar por nombre o cédula", placeholder="Ej: Valentina o 1032331000", key="q_search")
        with search_cols[1]:
            if _button("Buscar", key="btn_search_trigger", help="Ejecutar búsqueda", type="primary"):
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

        selected_idx = None
        modify_cols = st.columns([0.75, 0.25])
        with modify_cols[0]:
            st.markdown(" ")
        with modify_cols[1]:
            if _button("Modificar registro", key="btn_consulta_modify", disabled=len(filtered) != 1, type="secondary"):
                if len(filtered) == 1:
                    selected_idx = int(filtered.index[0])
                    row = df_latest.loc[selected_idx]
                    clean_row = row.drop(labels=HIDDEN_COLUMNS, errors="ignore")
                    ced_value = str(row.get("Cédula") or row.get("C?dula") or "").strip()
                    st.session_state["editing_target"] = {
                        "index": selected_idx,
                        "cedula": ced_value,
                        "nombre": str(row.get("Nombre_Usuario", "")).strip(),
                    }
                    st.session_state["pending_prefill_doc"] = ced_value
                    st.session_state["inline_edit_idx"] = selected_idx
                    st.session_state["inline_edit_data"] = clean_row.to_dict()
                    st.success("Registro listo para modificar (puedes editarlo abajo o en la pestaña Registrar).")
                    _streamlit_rerun()


        st.write(f"Registros encontrados: **{len(filtered)}**")
        inline_idx = st.session_state.get("inline_edit_idx")
        if inline_idx is not None:
            st.markdown("### Editar registro seleccionado")
            inline_data = st.session_state.get("inline_edit_data")
            if not inline_data:
                inline_data = (
                    df_latest.loc[inline_idx]
                    .drop(labels=HIDDEN_COLUMNS, errors="ignore")
                    .to_dict()
                )
            editable_df = pd.DataFrame([inline_data])
            edited_df = st.data_editor(
                editable_df,
                num_rows="fixed",
                use_container_width=True,
                key="inline_editor",
            )
            st.session_state["inline_edit_data"] = edited_df.iloc[0].to_dict()
            action_cols = st.columns([0.25, 0.25, 0.5])
            with action_cols[0]:
                if _button("Guardar cambios", key="btn_inline_save", type="primary"):
                    df_all = service.load_registro()
                    df_all.loc[inline_idx] = edited_df.iloc[0]
                    service.save_registro(df_all)
                    st.success("Registro actualizado correctamente.")
                    st.session_state.pop("inline_edit_idx", None)
                    st.session_state.pop("inline_edit_data", None)
                    st.session_state["reset_pending"] = True
                    _streamlit_rerun()
            with action_cols[1]:
                if _button("Cancelar edición", key="btn_inline_cancel", type="secondary"):
                    st.session_state.pop("inline_edit_idx", None)
                    st.session_state.pop("inline_edit_data", None)
                    _streamlit_rerun()
        cols_show = [
            c
            for c in [
                "Nombre_Usuario",
                "C\u00e9dula",
                "Correo_Electronico",
                "T\u00edtulo_Trabajo_Grado",
                "Nombre_Facultad",
                "Nombre_Programa",
                "Paz_y_Salvo",
                "Fecha",
            ]
            if c in filtered.columns and c not in HIDDEN_COLUMNS
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
            if inline_idx is not None and inline_idx in df_to_show.index:
                # Evita mostrar el mismo registro dos veces cuando se edita en línea.
                df_to_show = df_to_show.drop(index=inline_idx)
            if "_Fecha_sort" in df_to_show.columns:
                df_to_show = df_to_show.drop(columns="_Fecha_sort")
            if not df_to_show.empty:
                st.dataframe(df_to_show[cols_show], use_container_width=True)
            elif inline_idx is not None:
                st.info("El registro seleccionado se está mostrando en el editor superior.")
        else:
            st.info("No hay registros para mostrar.")
        st.download_button(
            label="Descargar archivo con registros",
            data=service.download_bytes(),
            file_name="registro_asesorias_actual.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _tab_normalizacion(tab, service: RegistroService, meta: dict) -> None:
    with tab:
        spacer_left, col_center, spacer_right = st.columns([0.12, 0.76, 0.12])
        with col_center:
            st.subheader("Normalización")
            st.markdown('<h3 style="font-size:1.2rem; margin-bottom:0.5rem;">Distribuir registros existentes</h3>', unsafe_allow_html=True)
            st.caption("La distribución se realiza por tesis; todos los estudiantes de una tesis quedan con la misma asignación.")
            default_people = getattr(config, "DEFAULT_ASSIGNMENT_PEOPLE", [])
            default_text = "\n".join(default_people)
            responsables_text = st.text_area(
                "Personas responsables en proceso de normalización:",
                value=default_text,
                key="assignment_people_text",
            )
            distribute = _button("Distribuir registros", type="primary")
            if distribute:
                responsables = [line.strip() for line in responsables_text.splitlines() if line.strip()]
                with st.spinner("Distribuyendo registros existentes..."):
                    try:
                        result = service.distribute_registros(responsables)
                    except Exception as exc:  # pragma: no cover - Streamlit feedback
                        st.error(f"No se pudo completar la distribución: {exc}")
                    else:
                        st.success("Distribución completada por tesis.")
                        st.info(
                            f"Tesis distribuidas: **{result.get('total_thesis', 0)}** · Estudiantes impactados: **{result.get('total_students', 0)}**"
                        )
                        st.caption(
                            f"Columna de asignación: {result.get('assignment_column')} · Columna de tesis: {result.get('thesis_column')}"
                        )
                        thesis_without = result.get("thesis_without_title", 0)
                        if thesis_without:
                            st.warning(
                                f"{thesis_without} tesis no tenían título registrado y se asignaron individualmente. Revísalas desde la pestaña Consultar usuario."
                            )
                        st.markdown("#### Resumen por persona")
                        summary_cols = st.columns(2)
                        for idx, (persona, data) in enumerate(result["counts"].items()):
                            tesis = data.get("tesis", 0)
                            estudiantes = data.get("estudiantes", 0)
                            with summary_cols[idx % 2]:
                                st.metric(persona, f"{tesis} tesis", f"{estudiantes} estudiantes")
                        ignored = result.get("ignored_rows", 0)
                        if ignored:
                            st.warning(
                                f"{ignored} filas se ignoraron por estar vacías o no tener nombre/cédula. "
                                "Puedes revisarlas en la pestaña Consultar usuario."
                            )

            st.markdown("---")
            st.markdown("### Normalización por responsable")
            responsables_opts = service.list_responsables()
            if not responsables_opts:
                st.info("Todavía no hay responsables definidos. Distribuye los registros para habilitar esta sección.")
            else:
                responsable = st.selectbox(
                    "Selecciona la persona responsable",
                    options=responsables_opts,
                    key="normalizacion_responsable",
                )
                if responsable:
                    try:
                        asignados_df = service.get_registros_por_responsable(responsable)
                    except Exception as exc:  # pragma: no cover
                        st.error(f"No se pudieron obtener los registros asignados: {exc}")
                    else:
                        if asignados_df.empty:
                            st.info("No hay estudiantes asignados a esta persona.")
                        else:
                            resumen = service.summarize_normalizacion(asignados_df)
                            metric_cols = st.columns(3)
                            metric_cols[0].metric("Total asignados", resumen["total"])
                            metric_cols[1].metric("Pendientes", resumen["pending"])
                            metric_cols[2].metric("OK", resumen["ok"])

                            try:
                                download_payload = service.build_responsable_excel(responsable)
                            except Exception as exc:  # pragma: no cover
                                st.error(f"No se pudo generar el archivo de descarga: {exc}")
                            else:
                                safe_name = responsable.lower().replace(" ", "_")
                                st.download_button(
                                    _download_label_for_responsable(responsable, context="normalizacion"),
                                    data=download_payload,
                                    file_name=f"normalizacion_{safe_name}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                )

                            status_col = config.NORMALIZATION_STATUS_COLUMN
                            obs_col = config.NORMALIZATION_OBS_COLUMN
                            ced_col = None
                            for candidate in ("C\u01f8dula", "C\u00e9dula", "C?dula", "Cedula"):
                                if candidate in asignados_df.columns:
                                    ced_col = candidate
                                    break
                            ced_values = (
                                asignados_df[ced_col].astype(str)
                                if ced_col
                                else [""] * len(asignados_df)
                            )
                            ok_value = (config.NORMALIZATION_OK_VALUE or "OK").upper()
                            programa_col = "Nombre_Programa" if "Nombre_Programa" in asignados_df.columns else None
                            thesis_source_col = RegistroService._tesis_column(asignados_df)
                            thesis_col = thesis_source_col or getattr(config, "THESIS_PRIMARY_COLUMN", "Título_Trabajo_Grado")
                            row_ids = asignados_df.index.astype(str)
                            edit_source = pd.DataFrame(
                                {
                                    "ID": row_ids,
                                    "Nombre": asignados_df.get("Nombre_Usuario", ""),
                                    "Cedula": ced_values,
                                    "Programa": asignados_df.get(programa_col, "") if programa_col else "",
                                    "Tesis": asignados_df.get(thesis_col, "") if thesis_col in asignados_df.columns else "",
                                    "Revisado": asignados_df[status_col]
                                    .fillna("")
                                    .astype(str)
                                    .str.upper()
                                    .eq(ok_value),
                                    "Observacion": asignados_df[obs_col].fillna("").astype(str),
                                }
                            )
                            edit_source = edit_source.set_index("ID")
                            column_config = {
                                "Nombre": st.column_config.TextColumn("Nombre de estudiante", disabled=True),
                                "Cedula": st.column_config.TextColumn("Cédula", disabled=True),
                                "Programa": st.column_config.TextColumn("Programa académico", disabled=True),
                                "Tesis": st.column_config.TextColumn("Trabajo de grado / tesis", disabled=True),
                                "Revisado": st.column_config.CheckboxColumn("Estado OK"),
                                "Observacion": st.column_config.TextColumn("Observación de normalización"),
                            }
                            edited_df = st.data_editor(
                                edit_source,
                                hide_index=True,
                                column_config=column_config,
                                key=f"editor_normalizacion_{responsable}",
                            )
                            if _button("Guardar avances", key=f"btn_save_normalizacion_{responsable}", type="primary"):
                                updates = []
                                for idx_row, row in edited_df.iterrows():
                                    updates.append(
                                        {
                                            "id": idx_row,
                                            "ok": bool(row["Revisado"]),
                                            "observacion": row.get("Observacion", ""),
                                        }
                                    )
                                with st.spinner("Guardando cambios en Google Sheets..."):
                                    try:
                                        resultado = service.update_normalizacion_estado(responsable, updates)
                                    except Exception as exc:  # pragma: no cover
                                        st.error(f"No se pudieron guardar los cambios: {exc}")
                                    else:
                                        st.success(
                                            f"Se actualizaron {resultado.get('updated', 0)} registros para {responsable}."
                                        )
                                        st.info(
                                            f"Pendientes: {resultado.get('pending', 0)} | OK: {resultado.get('ok', 0)}"
                                        )
                                        _streamlit_rerun()


def _tab_publicacion(tab, service: RegistroService, meta: dict) -> None:
    with tab:
        try:
            df_ready = service.get_publicacion_registros()
        except Exception as exc:  # pragma: no cover
            st.error(f"No se pudieron cargar los registros para publicación: {exc}")
            return
        summary = service.summarize_publicacion(df_ready)
        assigned = summary.get("assigned", {})
        metric_cols = st.columns(4)
        metric_cols[0].metric("Listos para publicación", summary.get("total", 0))
        metric_cols[1].metric("Pendientes", summary.get("pending", 0))
        metric_cols[2].metric("Publicados", summary.get("published", 0))
        metric_cols[3].metric("Asignados Gloria", assigned.get(config.PUBLICATION_PRIMARY, 0))
        support_name = config.PUBLICATION_RESPONSIBLES[1]
        st.metric("Asignados Diana", assigned.get(support_name, 0))
        responsables = service.list_publicacion_responsables()
        if not responsables:
            st.info("No hay responsables configurados para publicación.")
            return
        responsable = st.selectbox(
            "Responsable activo",
            options=responsables,
            key="publicacion_responsable",
        )
        if not responsable:
            st.info("Selecciona un responsable para ver sus registros.")
            return
        show_all = False
        primary_norm = (utils.norm_str(config.PUBLICATION_PRIMARY) or "").lower()
        responsable_norm = (utils.norm_str(responsable) or "").lower()
        if responsable_norm == primary_norm:
            show_all = st.checkbox(
                "Ver todos los pendientes de publicación",
                value=False,
                key="publicacion_show_all",
            )
        df_responsable = service.get_publicacion_registros(
            None if show_all else responsable,
            include_all_for_primary=show_all,
        )
        if df_responsable.empty:
            st.info("No hay registros listos para publicación con este filtro.")
            return
        try:
            download_payload = service.build_publicacion_excel(
                None if show_all else responsable,
                include_all_for_primary=show_all,
            )
        except ValueError:
            download_payload = None
        else:
            safe_name = (responsable.lower().replace(" ", "_")) if not show_all else "todos"
            st.download_button(
                _download_label_for_responsable(responsable if not show_all else "todos", show_all=show_all, context="publicacion"),
                data=download_payload,
                file_name=f"publicacion_{safe_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        assignment_col = config.PUBLICATION_ASSIGNMENT_COLUMN
        state_col = config.PUBLICATION_STATUS_COLUMN
        obs_col = config.PUBLICATION_OBS_COLUMN
        ced_col = RegistroService._cedula_column(df_responsable)
        ced_values = (
            df_responsable[ced_col].astype(str) if ced_col else [""] * len(df_responsable)
        )
        done_value = (config.PUBLICATION_DONE_VALUE or "Publicado").upper()
        row_ids = df_responsable.index.astype(str)
        edit_source = pd.DataFrame(
            {
                "ID": row_ids,
                "Nombre": df_responsable.get("Nombre_Usuario", ""),
                "Cedula": ced_values,
                "Asignado": df_responsable.get(assignment_col, ""),
                "Publicado": df_responsable[state_col].fillna("").astype(str).str.upper() == done_value,
                "Observacion": df_responsable[obs_col].fillna("").astype(str),
            }
        )
        edit_source = edit_source.set_index("ID")
        column_config = {
            "Nombre": st.column_config.TextColumn("Nombre de estudiante", disabled=True),
            "Cedula": st.column_config.TextColumn("Cédula", disabled=True),
            "Asignado": st.column_config.TextColumn("Asignado a", disabled=True),
            "Publicado": st.column_config.CheckboxColumn("Publicado"),
            "Observacion": st.column_config.TextColumn("Observación publicación"),
        }
        edited_df = st.data_editor(
            edit_source,
            hide_index=True,
            column_config=column_config,
            key=f"editor_publicacion_{responsable}",
        )
        if _button("Guardar publicación", key=f"btn_save_publicacion_{responsable}", type="primary"):
            updates = [
                {
                    "id": idx,
                    "ok": bool(row["Publicado"]),
                    "observacion": row.get("Observacion", ""),
                }
                for idx, row in edited_df.iterrows()
            ]
            with st.spinner("Guardando cambios en Google Sheets..."):
                try:
                    resultado = service.update_publicacion_estado(responsable, updates)
                except Exception as exc:  # pragma: no cover
                    st.error(f"No se pudieron guardar los cambios: {exc}")
                else:
                    st.success(
                        f"Se actualizaron {resultado.get('updated', 0)} registros de {responsable}."
                    )
                    st.info(
                        f"Pendientes: {resultado.get('pending', 0)} | Publicados: {resultado.get('published', 0)}"
                    )
                    _streamlit_rerun()
        if responsable_norm == primary_norm:
            st.markdown("---")
            st.markdown("#### Asignar registros a Diana Patricia Salazar")
            pending_gloria = service.get_publicacion_registros(
                config.PUBLICATION_PRIMARY, only_pending=True
            )
            if pending_gloria.empty:
                st.info("No hay registros pendientes para reasignar.")
            else:
                ced_col_pending = RegistroService._cedula_column(pending_gloria)
                options = []
                display_to_id = {}
                for _, row in pending_gloria.iterrows():
                    label = row.get("Nombre_Usuario", "Sin nombre")
                    ced_val = row.get(ced_col_pending, "") if ced_col_pending else ""
                    uid = str(row.name)
                    text = f"{label} ({ced_val}) - {uid}"
                    options.append(text)
                    display_to_id[text] = uid
                seleccion = st.multiselect(
                    "Selecciona registros para enviar a Diana",
                    options=options,
                    key="publicacion_assign_list",
                )
                if _button("Asignar a Diana", key="btn_assign_publicacion", type="primary"):
                    ids_to_assign = [display_to_id[label] for label in seleccion]
                    if not ids_to_assign:
                        st.warning("Selecciona al menos un registro para reasignar.")
                    else:
                        with st.spinner("Actualizando asignaciones..."):
                            try:
                                updated = service.assign_publicacion(
                                    config.PUBLICATION_PRIMARY, ids_to_assign, support_name
                                )
                            except Exception as exc:  # pragma: no cover
                                st.error(f"No se pudo reasignar: {exc}")
                            else:
                                st.success(f"Se reasignaron {updated} registros a {support_name}.")
                                _streamlit_rerun()


def _tab_dashboard(tab, service: RegistroService, meta: dict) -> None:
    with tab:
        df_base = service.build_dashboard_dataframe()
        if df_base.empty:
            st.info('No hay datos suficientes para mostrar métricas.')
            return

        min_date = df_base['Fecha'].min().date() if 'Fecha' in df_base.columns else None
        max_date = df_base['Fecha'].max().date() if 'Fecha' in df_base.columns else None
        default_range = (min_date, max_date) if (min_date and max_date) else None
        st.markdown("### Filtros")
        date_filter = st.date_input(
            'Rango de fechas (según la fecha de registro)',
            value=default_range if default_range else None,
            help='Selecciona la fecha de inicio y fin para limitar los registros analizados.',
            key='dashboard_date_range',
        )
        filter_cols = st.columns(2)
        responsables_opts = sorted(
            {utils.norm_str(val) or '' for val in df_base.get(config.ASSIGNMENT_COLUMN, pd.Series()).tolist() if val}
        )
        with filter_cols[0]:
            responsables_sel = st.multiselect(
                'Responsable asignado',
                options=responsables_opts,
                help='Filtra por la persona encargada de la tesis.',
            )
        stage_options = ['Registradas', 'En proceso', 'Normalizadas', 'Con observaciones', 'Publicadas']
        with filter_cols[1]:
            stage_sel = st.multiselect(
                'Estado del proceso',
                options=stage_options,
                help='Selecciona una o varias etapas para enfocar las métricas.',
            )
        start_date = date_filter[0] if isinstance(date_filter, tuple) and len(date_filter) == 2 else None
        end_date = date_filter[1] if isinstance(date_filter, tuple) and len(date_filter) == 2 else None
        df_filtered_base = service.filter_dashboard_dataframe(
            df_base,
            start_date=start_date,
            end_date=end_date,
            responsables=responsables_sel or None,
        )
        df_filtered = df_filtered_base.copy()
        if stage_sel and not df_filtered_base.empty:
            stage_masks = service.dashboard_stage_masks(df_filtered_base)
            combined_mask = pd.Series(False, index=df_filtered_base.index, dtype=bool)
            for stage in stage_sel:
                mask = stage_masks.get(stage)
                if mask is not None:
                    combined_mask |= mask
            df_filtered = df_filtered_base.loc[combined_mask]

        metrics = service.calculate_dashboard_metrics(df_filtered)
        general = metrics['general']
        kpi_cols = st.columns(5)
        kpi_cols[0].metric('Total registradas', general['total'])
        kpi_cols[1].metric('En proceso', general['en_proceso'])
        kpi_cols[2].metric('Normalizadas', general['normalizadas'])
        kpi_cols[3].metric('Con observaciones', general['con_observaciones'])
        kpi_cols[4].metric('Publicadas', general['publicadas'], f"{general['avance']}% avance")

        st.subheader('Distribución por etapa')
        stage_data = [
            ('Registradas', general['total']),
            ('En proceso', general['en_proceso']),
            ('Normalizadas', general['normalizadas']),
            ('Con observaciones', general['con_observaciones']),
            ('Publicadas', general['publicadas']),
        ]
        stage_df = pd.DataFrame(stage_data, columns=['Etapa', 'Cantidad'])
        stage_df['Etiqueta'] = stage_df['Cantidad'].apply(lambda v: '' if v == 0 else str(v))
        colors = ['#186f65', '#2f8f83', '#48b19b', '#a3e6c9', '#94a3b8']
        fig = go.Figure(
            data=[
                go.Bar(
                    x=stage_df['Etapa'],
                    y=stage_df['Cantidad'],
                    marker_color=colors[: len(stage_df)],
                    text=stage_df['Etiqueta'],
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>Cantidad: %{y}<extra></extra>',
                )
            ]
        )
        fig.update_layout(
            template='simple_white',
            xaxis_title='Etapa del proceso',
            yaxis_title='Cantidad de tesis',
            uniformtext_minsize=10,
            uniformtext_mode='show',
            margin=dict(t=60, b=40, l=40, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader('Descarga de métricas')
        export_df = df_filtered.copy()
        summary_rows = [
            {'Indicador': 'Total registradas', 'Valor': general['total']},
            {'Indicador': 'En proceso', 'Valor': general['en_proceso']},
            {'Indicador': 'Normalizadas', 'Valor': general['normalizadas']},
            {'Indicador': 'Con observaciones', 'Valor': general['con_observaciones']},
            {'Indicador': 'Publicadas', 'Valor': general['publicadas']},
        ]
        summary_df = pd.DataFrame(summary_rows)
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Datos')
            summary_df.to_excel(writer, index=False, sheet_name='Resumen')
        excel_buffer.seek(0)
        csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
        download_cols = st.columns(2)
        download_cols[0].download_button(
            'Descargar Excel',
            data=excel_buffer.getvalue(),
            file_name='metricas_tesis.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        download_cols[1].download_button(
            'Descargar CSV',
            data=csv_data,
            file_name='metricas_tesis.csv',
            mime='text/csv',
        )


def render_app() -> None:
    service = RegistroService()
    if not TEMPLATE_PATH.exists():
        st.error(
            f"No encuentro el template en: {TEMPLATE_PATH}\n\nDebe existir: data/Control_Asesorias_Tesis_template.xlsm"
        )
        return
    try:
        meta = service.load_lists()
    except Exception as exc:
        st.error(f"No se pudieron cargar las listas de apoyo: {exc}")
        return
    _render_tabs(service, meta)
