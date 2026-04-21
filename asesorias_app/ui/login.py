"""Pantalla de login y barra de sesion para controlTesis."""

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
    """Dibuja una pantalla de inicio de sesion simple."""
    st.session_state.setdefault("login_email", "")
    st.session_state.setdefault("login_password", "")
    st.session_state.setdefault("login_password_reset", False)
    if st.session_state.get("login_password_reset"):
        st.session_state["login_password"] = ""
        st.session_state["login_password_reset"] = False

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
        with st.form("tf_login_form", border=False, clear_on_submit=False):
            email = st.text_input(
                "Correo institucional",
                key="login_email",
                placeholder="usuario@umanizales.edu.co",
            )
            password = st.text_input(
                "Contrasena",
                key="login_password",
                type="password",
                placeholder="Contrasena",
            )
            submitted_login = st.form_submit_button("Iniciar sesion", use_container_width=True)

        error_msg = st.session_state.get(LOGIN_ERROR_KEY)
        if error_msg:
            st.markdown(f'<div class="tf-login-alert">{error_msg}</div>', unsafe_allow_html=True)

    if submitted_login:
        user = auth_service.authenticate(email, password)
        if user is None:
            st.session_state[LOGIN_ERROR_KEY] = "Credenciales invalidas. Verifica correo y contrasena."
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
    """Muestra la identidad del usuario activo y opcion de cierre de sesion."""
    _, action_col = st.columns([0.8, 0.2])
    with action_col:
        if st.button("Cerrar sesion", key="tf_logout_button"):
            logout()


def render_session_footer(user: AuthUser) -> None:
    """Muestra los datos del usuario al final de la aplicacion."""
    st.markdown(
        f"""
<div class="tf-user-footer">
    <div class="tf-user-footer__name">{user.name}</div>
    <div class="tf-user-footer__meta">{user.email} · {user.role.title()}</div>
</div>
""",
        unsafe_allow_html=True,
    )
