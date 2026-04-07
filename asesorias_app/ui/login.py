"""Pantalla de login y barra de sesión para controlTesis."""

from __future__ import annotations

import time
from typing import Optional

import streamlit as st

from asesorias_app.auth import service as auth_service
from asesorias_app.auth.service import AuthUser

SESSION_USER_KEY = "tf_auth_user"
SESSION_LAST_ACTIVE_KEY = "tf_auth_last_active"
SESSION_TIMEOUT_SECONDS = 3600
LOGIN_ERROR_KEY = "_tf_login_error"
SUPPORT_EMAIL = "biblio_data@umanizales.edu.co"


def get_current_user() -> Optional[AuthUser]:
    user_data = st.session_state.get(SESSION_USER_KEY)
    if isinstance(user_data, AuthUser):
        payload = {
            "email": user_data.email,
            "name": user_data.name,
            "role": user_data.role,
            "must_reset": user_data.must_reset,
        }
        st.session_state[SESSION_USER_KEY] = payload
        user_data = payload
    if not isinstance(user_data, dict):
        return None
    last_active = st.session_state.get(SESSION_LAST_ACTIVE_KEY, 0)
    if time.time() - float(last_active or 0) > SESSION_TIMEOUT_SECONDS:
        _set_current_user(None)
        return None
    st.session_state[SESSION_LAST_ACTIVE_KEY] = time.time()
    return AuthUser(**user_data)


def _set_current_user(user: Optional[AuthUser]) -> None:
    if user is None:
        st.session_state.pop(SESSION_USER_KEY, None)
        st.session_state.pop(SESSION_LAST_ACTIVE_KEY, None)
    else:
        st.session_state[SESSION_USER_KEY] = {
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "must_reset": user.must_reset,
        }
        st.session_state[SESSION_LAST_ACTIVE_KEY] = time.time()


def _streamlit_rerun() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
    else:  # pragma: no cover
        st.experimental_rerun()


def render_login_page() -> None:
    """Dibuja la pantalla de inicio de sesión institucional."""
    st.session_state.setdefault("login_email", "")
    st.session_state.setdefault("login_password", "")
    st.session_state.setdefault("login_password_reset", False)
    st.session_state.setdefault("login_mode", "login")
    st.session_state.setdefault("login_activation_email", "")
    st.session_state.setdefault("login_activation_password", "")
    st.session_state.setdefault("login_activation_confirm", "")
    st.session_state.setdefault("login_activation_reset", False)
    if st.session_state.get("login_password_reset"):
        st.session_state["login_password"] = ""
        st.session_state["login_password_reset"] = False
    if st.session_state.get("login_activation_reset"):
        st.session_state["login_activation_email"] = ""
        st.session_state["login_activation_password"] = ""
        st.session_state["login_activation_confirm"] = ""
        st.session_state["login_activation_reset"] = False

    st.markdown(
        """
<section class="tf-login-hero">
    <div class="tf-login-banner">
        <h1>ControlTesis</h1>
    </div>
</section>
""",
        unsafe_allow_html=True,
    )

    submitted_login = False
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        if st.session_state["login_mode"] == "login":
            with st.form("tf_login_form", border=False, clear_on_submit=False):
                email = st.text_input(
                    "Correo institucional",
                    key="login_email",
                    placeholder="usuario@umanizales.edu.co",
                )
                password = st.text_input(
                    "Contraseña",
                    key="login_password",
                    type="password",
                    placeholder="Contraseña",
                )
                submitted_login = st.form_submit_button("Iniciar sesión", use_container_width=True)
            activate_col, recover_col = st.columns(2)
            with activate_col:
                if st.button("Confirmar contraseña por primera vez", use_container_width=True):
                    st.session_state["login_mode"] = "activation"
                    _streamlit_rerun()
            with recover_col:
                if st.button("Olvidé mi contraseña", use_container_width=True):
                    st.session_state["login_mode"] = "recovery"
                    _streamlit_rerun()
        elif st.session_state["login_mode"] in {"activation", "recovery"}:
            mode_title = "Registrar contraseña" if st.session_state["login_mode"] == "activation" else "Actualizar contraseña"
            with st.form("tf_activation_form", border=False, clear_on_submit=False):
                act_email = st.text_input(
                    "Correo institucional",
                    key="login_activation_email",
                    placeholder="usuario@umanizales.edu.co",
                )
                act_password = st.text_input(
                    "Nueva contraseña",
                    key="login_activation_password",
                    type="password",
                )
                act_confirm = st.text_input(
                    "Confirma la contraseña",
                    key="login_activation_confirm",
                    type="password",
                )
                activation_submit = st.form_submit_button(mode_title, use_container_width=True)
            if activation_submit:
                activation_email_clean = (act_email or "").strip()
                if not activation_email_clean or not act_password:
                    st.error("Completa el correo institucional y la nueva contraseña.")
                elif len(act_password) < 8:
                    st.error("La contraseña debe tener al menos 8 caracteres.")
                elif act_password != act_confirm:
                    st.error("Las contraseñas no coinciden.")
                elif not auth_service.ensure_user_record(activation_email_clean):
                    st.error("Ese correo no está autorizado para controlTesis.")
                else:
                    ok = auth_service.set_initial_password(
                        activation_email_clean,
                        act_password,
                        force=True,
                    )
                    if ok:
                        st.success("Contraseña registrada. Ahora puedes iniciar sesión.")
                        st.session_state["login_mode"] = "login"
                        st.session_state["login_activation_reset"] = True
                        _streamlit_rerun()
                    else:
                        st.error("No se pudo actualizar la contraseña. Verifica los datos ingresados.")
            if st.button("Volver al inicio de sesión", use_container_width=True):
                st.session_state["login_mode"] = "login"
                _streamlit_rerun()

        error_msg = st.session_state.get(LOGIN_ERROR_KEY)
        if error_msg:
            st.markdown(f'<div class="tf-login-alert">{error_msg}</div>', unsafe_allow_html=True)

    if st.session_state["login_mode"] == "login":
        st.session_state["show_activation_form"] = False

    st.markdown(
        f"""
<div class="tf-login-support-row">
    <div class="tf-login-support">
        <span>Soporte institucional</span>
        <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if submitted_login:
        user = auth_service.authenticate(email, password)
        if user is None:
            st.session_state[LOGIN_ERROR_KEY] = "Credenciales inválidas. Verifica correo y contraseña."
            st.session_state["login_password_reset"] = True
        elif user.must_reset:
            st.session_state[LOGIN_ERROR_KEY] = "Activa tu acceso antes de ingresar."
            st.session_state["login_password_reset"] = True
        else:
            st.session_state[LOGIN_ERROR_KEY] = ""
            st.session_state["login_password_reset"] = True
            _set_current_user(user)
            _streamlit_rerun()


def logout() -> None:
    _set_current_user(None)
    st.session_state.pop("login_email", None)
    st.session_state.pop("login_password", None)
    st.session_state.pop(LOGIN_ERROR_KEY, None)
    _streamlit_rerun()


def render_session_header(user: AuthUser) -> None:
    """Muestra la identidad del usuario activo y opción de cierre de sesión."""
    info_col, action_col = st.columns([0.8, 0.2])
    with info_col:
        st.markdown(
            f"""
<div class="tf-user-id">
    <div class="tf-user-name">{user.name}</div>
    <div class="tf-user-meta">{user.email} · {user.role.title()}</div>
</div>
""",
            unsafe_allow_html=True,
        )
    with action_col:
        if st.button("Cerrar sesión", key="tf_logout_button"):
            logout()
