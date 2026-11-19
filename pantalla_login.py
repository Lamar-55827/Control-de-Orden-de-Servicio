"""Pantalla de inicio de sesión y manejo de sesión."""

import streamlit as st

from config_settings import APP_NOMBRE, EMPRESA, ESLOGAN
import db_usuarios

MAX_INTENTOS = 5


def usuario_actual():
    """Devuelve el usuario autenticado de la sesión o None."""
    return st.session_state.get("usuario")


def cerrar_sesion():
    """Limpia por completo la sesión del usuario."""
    for clave in list(st.session_state.keys()):
        del st.session_state[clave]


def render_login():
    """Dibuja el formulario de acceso."""
    _, centro, _ = st.columns([1, 1.3, 1])

    with centro:
        st.markdown(
            f'<div class="login-card"><div class="login-marca">🔧 {EMPRESA.upper()}</div>'
            f'<div class="login-sistema">{APP_NOMBRE}</div>'
            f'<div class="login-eslogan">{ESLOGAN}</div></div>',
            unsafe_allow_html=True,
        )

        intentos = st.session_state.get("intentos_login", 0)
        if intentos >= MAX_INTENTOS:
            st.error("Demasiados intentos fallidos. Recarga la página para intentarlo de nuevo.")
            return

        with st.form("form_login"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            enviado = st.form_submit_button("Iniciar sesión", type="primary")

        if not enviado:
            return

        if not username.strip() or not password:
            st.warning("Escribe tu usuario y contraseña.")
            return

        try:
            usuario = db_usuarios.autenticar(username, password)
        except Exception as error:
            st.error(
                "No fue posible conectar con la base de datos. Verifica DATABASE_URL "
                "y que hayas ejecutado schema.sql."
            )
            st.caption(f"Detalle técnico: {error}")
            return

        if usuario:
            st.session_state["usuario"] = usuario
            st.session_state["intentos_login"] = 0
            st.rerun()
        else:
            st.session_state["intentos_login"] = intentos + 1
            st.error("Usuario o contraseña incorrectos.")
