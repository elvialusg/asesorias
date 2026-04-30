"""Pantalla de login y barra de sesion para controlTesis."""

from __future__ import annotations

import base64
import html
import time
from typing import Optional

import streamlit as st

from asesorias_app import config
from asesorias_app.auth import service as auth_service
from asesorias_app.auth.service import AuthUser

SESSION_USER_KEY = "tf_auth_user"
SESSION_LAST_ACTIVE_KEY = "tf_auth_last_active"
SESSION_TIMEOUT_SECONDS = 3600
LOGIN_ERROR_KEY = "_tf_login_error"
LOGIN_ATTEMPTS_KEY = "_tf_login_attempts"
LOGIN_LOCK_UNTIL_KEY = "_tf_login_lock_until"
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCK_SECONDS = 15 * 60
LOGIN_FAILURES: dict[str, dict[str, float]] = {}


def _login_key(email: str) -> str:
    return (email or "").strip().lower()


def _login_logo_html() -> str:
    logo_path = getattr(config, "LOGIN_LOGO_PATH", None)
    if not logo_path or not logo_path.exists():
        return ""
    encoded_logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"""
<div class="tf-login-brand">
    <img
        src="data:image/png;base64,{encoded_logo}"
        alt="Biblioteca y Centro de Recursos Universidad de Manizales"
        class="tf-login-brand__logo"
    />
</div>
"""


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
        f"""
<section class="tf-login-hero">
    <div class="tf-login-banner">
        <h1>ControlTesis</h1>
    </div>
    {_login_logo_html()}
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
        login_key = _login_key(email)
        failure_state = LOGIN_FAILURES.get(login_key, {})
        lock_until = max(
            float(st.session_state.get(LOGIN_LOCK_UNTIL_KEY, 0) or 0),
            float(failure_state.get("lock_until", 0) or 0),
        )
        if lock_until > time.time():
            remaining = int((lock_until - time.time()) // 60) + 1
            st.session_state[LOGIN_ERROR_KEY] = (
                f"Demasiados intentos fallidos. Intenta de nuevo en {remaining} min."
            )
            st.session_state["login_password_reset"] = True
            _streamlit_rerun()
            return

        user = auth_service.authenticate(email, password)
        if user is None:
            attempts = int(failure_state.get("attempts", st.session_state.get(LOGIN_ATTEMPTS_KEY, 0)) or 0) + 1
            st.session_state[LOGIN_ATTEMPTS_KEY] = attempts
            LOGIN_FAILURES[login_key] = {"attempts": float(attempts), "lock_until": 0}
            if attempts >= MAX_LOGIN_ATTEMPTS:
                lock_until = time.time() + LOGIN_LOCK_SECONDS
                st.session_state[LOGIN_LOCK_UNTIL_KEY] = lock_until
                st.session_state[LOGIN_ATTEMPTS_KEY] = 0
                LOGIN_FAILURES[login_key] = {"attempts": 0, "lock_until": lock_until}
                st.session_state[LOGIN_ERROR_KEY] = (
                    "Demasiados intentos fallidos. Intenta de nuevo en 15 min."
                )
            else:
                remaining = MAX_LOGIN_ATTEMPTS - attempts
                st.session_state[LOGIN_ERROR_KEY] = (
                    f"Credenciales invalidas. Quedan {remaining} intentos antes del bloqueo temporal."
                )
            st.session_state["login_password_reset"] = True
        else:
            st.session_state[LOGIN_ERROR_KEY] = ""
            st.session_state[LOGIN_ATTEMPTS_KEY] = 0
            st.session_state[LOGIN_LOCK_UNTIL_KEY] = 0
            LOGIN_FAILURES.pop(login_key, None)
            st.session_state["login_password_reset"] = True
            _set_current_user(user)
            _streamlit_rerun()


def logout() -> None:
    _set_current_user(None)
    st.session_state.pop("login_email", None)
    st.session_state.pop("login_password", None)
    st.session_state.pop(LOGIN_ERROR_KEY, None)
    st.session_state.pop(LOGIN_ATTEMPTS_KEY, None)
    st.session_state.pop(LOGIN_LOCK_UNTIL_KEY, None)
    _streamlit_rerun()


def render_session_header(user: AuthUser) -> None:
    """Muestra la identidad del usuario activo y opcion de cierre de sesion."""
    _, action_col = st.columns([0.8, 0.2])
    with action_col:
        if st.button("Cerrar sesion", key="tf_logout_button"):
            logout()


def render_session_footer(user: AuthUser) -> None:
    """Muestra los datos del usuario al final de la aplicacion."""
    name = html.escape(user.name)
    email = html.escape(user.email)
    role = html.escape(user.role.title())
    st.markdown(
        f"""
<div class="tf-user-footer">
    <div class="tf-user-footer__name">{name}</div>
    <div class="tf-user-footer__meta">{email} · {role}</div>
</div>
""",
        unsafe_allow_html=True,
    )
