"""Pantalla de login y barra de sesión para TesisFlow."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from asesorias_app.auth import service as auth_service
from asesorias_app.auth.service import AuthUser

SESSION_USER_KEY = "tf_auth_user"
LOGIN_ERROR_KEY = "_tf_login_error"
SUPPORT_EMAIL = "biblio_data@umanizales.edu.co"


def get_current_user() -> Optional[AuthUser]:
    user = st.session_state.get(SESSION_USER_KEY)
    if isinstance(user, AuthUser):
        return user
    return None


def _set_current_user(user: Optional[AuthUser]) -> None:
    if user is None:
        st.session_state.pop(SESSION_USER_KEY, None)
    else:
        st.session_state[SESSION_USER_KEY] = user


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
    if st.session_state.get("login_password_reset"):
        st.session_state["login_password"] = ""
        st.session_state["login_password_reset"] = False

    st.markdown(
        """
<section class="tf-login-hero">
    <div class="tf-login-banner">
        <h1>TesisFlow</h1>
        <p class="tf-login-copy">
            Acceso exclusivo para personal institucional autorizado.
        </p>
    </div>
</section>
""",
        unsafe_allow_html=True,
    )

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
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
            submitted = st.form_submit_button("Iniciar sesión", use_container_width=True)

        error_msg = st.session_state.get(LOGIN_ERROR_KEY)
        if error_msg:
            st.markdown(f'<div class="tf-login-alert">{error_msg}</div>', unsafe_allow_html=True)

        st.markdown('<div class="tf-login-tools">', unsafe_allow_html=True)
        tabs = st.tabs(["Activar acceso", "Cambiar contraseña", "Recuperar acceso"])

        with tabs[0]:
            with st.form("tf_activation_form", border=False, clear_on_submit=False):
                activation_email = st.text_input(
                    "Correo institucional",
                    key="activation_email",
                    placeholder="usuario@umanizales.edu.co",
                )
                activation_password = st.text_input(
                    "Nueva contraseña",
                    key="activation_password",
                    type="password",
                )
                activation_confirm = st.text_input(
                    "Confirma la contraseña",
                    key="activation_confirm",
                    type="password",
                )
                activation_submit = st.form_submit_button("Activar cuenta", use_container_width=True)
            if activation_submit:
                activation_email_clean = (activation_email or "").strip()
                if not activation_email_clean or not activation_password:
                    st.error("Completa el correo institucional y la nueva contraseña.")
                elif activation_password != activation_confirm:
                    st.error("Las contraseñas no coinciden.")
                elif not auth_service.ensure_user_record(activation_email_clean):
                    st.error("Ese correo no está autorizado para TesisFlow.")
                else:
                    needs_setup = auth_service.needs_password_setup(activation_email_clean)
                    ok = auth_service.set_initial_password(
                        activation_email_clean, activation_password, force=True
                    )
                    if ok and needs_setup:
                        st.success("Activaste tu cuenta. Puedes ingresar con la nueva contraseña.")
                    elif ok:
                        st.info("La cuenta ya existía, actualizamos tu contraseña y bloqueamos accesos anteriores.")
                    else:
                        st.error("No se pudo activar la cuenta. Verifica los datos ingresados.")

        with tabs[1]:
            with st.form("tf_change_form", border=False, clear_on_submit=False):
                change_email = st.text_input(
                    "Correo institucional",
                    key="change_email",
                    placeholder="usuario@umanizales.edu.co",
                )
                current_password = st.text_input(
                    "Contraseña actual",
                    key="change_current_password",
                    type="password",
                )
                new_password = st.text_input(
                    "Nueva contraseña",
                    key="change_new_password",
                    type="password",
                )
                new_password_confirm = st.text_input(
                    "Confirma la nueva contraseña",
                    key="change_confirm_password",
                    type="password",
                )
                change_submit = st.form_submit_button("Cambiar contraseña", use_container_width=True)
            if change_submit:
                change_email_clean = (change_email or "").strip()
                if not change_email_clean or not current_password or not new_password:
                    st.error("Todos los campos son obligatorios para cambiar la contraseña.")
                elif new_password != new_password_confirm:
                    st.error("Las contraseñas nuevas no coinciden.")
                elif auth_service.change_password(change_email_clean, current_password, new_password):
                    st.success("Actualizamos tu contraseña correctamente.")
                else:
                    st.error("No pudimos cambiar la contraseña. Revisa tus credenciales.")

        with tabs[2]:
            request_col, apply_col = st.columns(2)
            with request_col:
                with st.form("tf_request_reset_form", border=False, clear_on_submit=False):
                    reset_email = st.text_input(
                        "Correo institucional",
                        key="reset_email",
                        placeholder="usuario@umanizales.edu.co",
                    )
                    request_submit = st.form_submit_button("Generar código temporal", use_container_width=True)
                if request_submit:
                    reset_email_clean = (reset_email or "").strip()
                    if not reset_email_clean:
                        st.error("Ingresa el correo para generar el código temporal.")
                    else:
                        token = auth_service.create_reset_token(reset_email_clean)
                        if token:
                            st.success(
                                f"Código temporal generado: {token}. Úsalo en la sección de restablecimiento."
                            )
                        else:
                            st.error("No se encontró un usuario con ese correo.")
            with apply_col:
                with st.form("tf_reset_form", border=False, clear_on_submit=False):
                    reset_apply_email = st.text_input(
                        "Correo institucional",
                        key="reset_apply_email",
                        placeholder="usuario@umanizales.edu.co",
                    )
                    reset_token = st.text_input(
                        "Código temporal",
                        key="reset_token",
                        placeholder="ABC123",
                    )
                    reset_new_password = st.text_input(
                        "Nueva contraseña",
                        key="reset_new_password",
                        type="password",
                    )
                    reset_confirm_password = st.text_input(
                        "Confirma la nueva contraseña",
                        key="reset_confirm_password",
                        type="password",
                    )
                    reset_submit = st.form_submit_button("Restablecer contraseña", use_container_width=True)
                if reset_submit:
                    reset_apply_email_clean = (reset_apply_email or "").strip()
                    reset_token_clean = (reset_token or "").strip()
                    if not reset_apply_email_clean or not reset_token_clean or not reset_new_password:
                        st.error("Completa todos los campos para restablecer la contraseña.")
                    elif reset_new_password != reset_confirm_password:
                        st.error("Las contraseñas nuevas no coinciden.")
                    elif auth_service.reset_password(
                        reset_apply_email_clean, reset_token_clean, reset_new_password
                    ):
                        st.success("Contraseña actualizada. Inicia sesión con tu nuevo acceso.")
                    else:
                        st.error("No fue posible restablecer la contraseña. Verifica el código temporal.")

        st.markdown("</div>", unsafe_allow_html=True)

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

    if submitted:
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
    st.markdown(
        """
<div class="tf-session-heading">
    <div>
        <p class="tf-session-eyebrow">Sesión institucional</p>
        <h2>Control de asesorías TesisFlow</h2>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    info_col, action_col = st.columns([0.7, 0.3])
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
        if st.button("Cerrar sesión", key="tf_logout_button", use_container_width=True):
            logout()
