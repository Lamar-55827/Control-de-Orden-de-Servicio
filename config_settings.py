"""Configuración central: identidad visual, roles, estados y permisos."""

import os

# ---------------------------------------------------------------------------
# Identidad corporativa
# ---------------------------------------------------------------------------
EMPRESA = "Dryg Tools"
APP_NOMBRE = "Sistema de Gestión de Reportes y Servicios"
ESLOGAN = "Especialistas en Herramientas de Torque"
FOLIO_PREFIJO = "DRYG"

COLOR_HEADER = "#D32F2F"    # Rojo industrial
COLOR_SIDEBAR = "#1E272C"   # Antracita
COLOR_MODULO = "#003B73"    # Azul marino institucional

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
ROL_VENDEDOR = "VENDEDOR"
ROL_TECNICO = "TECNICO"
ROL_ADMIN = "ADMINISTRADOR"
ROLES = (ROL_VENDEDOR, ROL_TECNICO, ROL_ADMIN)

ROL_ETIQUETAS = {
    ROL_VENDEDOR: "Vendedor",
    ROL_TECNICO: "Técnico",
    ROL_ADMIN: "Administrador",
}

# ---------------------------------------------------------------------------
# Estados, prioridades y tipos de servicio
# ---------------------------------------------------------------------------
ESTADOS = [
    "Recibido",
    "En Diagnóstico",
    "En Reparación",
    "Esperando Refacciones",
    "Listo para Entrega",
    "Entregado",
    "Cancelado",
]
ESTADOS_FINALES = ("Entregado", "Cancelado")

ESTADO_COLORES = {
    "Recibido": "#607D8B",
    "En Diagnóstico": "#0277BD",
    "En Reparación": "#EF6C00",
    "Esperando Refacciones": "#8E24AA",
    "Listo para Entrega": "#2E7D32",
    "Entregado": "#1B5E20",
    "Cancelado": "#B71C1C",
}

PRIORIDADES = ["Baja", "Media", "Alta", "Urgente"]

TIPOS_SERVICIO = [
    "Reparación",
    "Calibración",
    "Mantenimiento preventivo",
    "Diagnóstico",
    "Garantía",
    "Otro",
]

# Tamaño máximo de cada evidencia (MB)
MAX_EVIDENCIA_MB = 5

# ---------------------------------------------------------------------------
# Menú de navegación por rol
# ---------------------------------------------------------------------------
MENU_INICIO = "🏠 Inicio"
MENU_CLIENTES = "👥 Clientes"
MENU_REPORTES = "📝 Reportes de Servicio"
MENU_USUARIOS = "🔐 Usuarios"

MENU_POR_ROL = {
    ROL_VENDEDOR: [MENU_INICIO, MENU_CLIENTES, MENU_REPORTES],
    ROL_TECNICO: [MENU_INICIO, MENU_CLIENTES, MENU_REPORTES],
    ROL_ADMIN: [MENU_INICIO, MENU_CLIENTES, MENU_REPORTES, MENU_USUARIOS],
}

# ---------------------------------------------------------------------------
# Permisos por rol (validados desde la lógica, no solo desde la interfaz)
# ---------------------------------------------------------------------------
_PERMISOS_BASE = {
    "clientes.ver",
    "clientes.crear",
    "reportes.ver",
    "reportes.crear",
    "reportes.pdf",
    "reportes.evidencias",
}

PERMISOS = {
    ROL_VENDEDOR: set(_PERMISOS_BASE),
    ROL_TECNICO: _PERMISOS_BASE | {"reportes.cambiar_estado"},
    ROL_ADMIN: _PERMISOS_BASE
    | {
        "clientes.editar",
        "reportes.cambiar_estado",
        "reportes.asignar",
        "reportes.ver_todos",
        "usuarios.gestionar",
    },
}


def tiene_permiso(rol, permiso):
    """Devuelve True si el rol tiene el permiso indicado."""
    return permiso in PERMISOS.get(rol, set())


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def get_database_url():
    """Obtiene DATABASE_URL desde st.secrets o desde la variable de entorno."""
    try:
        import streamlit as st

        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "No se encontró DATABASE_URL. Defínela en .streamlit/secrets.toml "
            "o como variable de entorno."
        )
    return url
