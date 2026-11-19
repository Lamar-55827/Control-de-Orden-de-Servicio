"""Gestión de usuarios y autenticación (contraseñas con bcrypt)."""

import re

import bcrypt
from psycopg2 import errors as pg_errors

from config_settings import ROLES, ROL_ADMIN, ROL_TECNICO, tiene_permiso
from db_connection import execute, fetch_all, fetch_one

_CAMPOS_PUBLICOS = "id, username, nombre_completo, rol, activo, creado_en"


def hash_password(password):
    """Genera el hash bcrypt de una contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_password(password, password_hash):
    """Compara una contraseña con su hash bcrypt."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


def autenticar(username, password):
    """Devuelve el usuario (sin hash) si las credenciales son válidas; si no, None."""
    username = (username or "").strip()
    if not username or not password:
        return None

    usuario = fetch_one(
        "SELECT id, username, nombre_completo, rol, activo, password_hash "
        "FROM usuarios WHERE LOWER(username) = LOWER(%s)",
        (username,),
    )
    if not usuario or not usuario["activo"]:
        return None
    if not verificar_password(password, usuario["password_hash"]):
        return None

    usuario.pop("password_hash", None)
    return usuario


def _validar_password(password):
    if not password or len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede exceder 72 bytes.")


def crear_usuario(username, nombre_completo, password, rol, actor=None):
    """Crea un usuario. Si se indica `actor`, valida que sea administrador."""
    if actor is not None and not tiene_permiso(actor["rol"], "usuarios.gestionar"):
        raise PermissionError("No tienes permiso para gestionar usuarios.")

    username = (username or "").strip().lower()
    nombre_completo = (nombre_completo or "").strip()

    if not re.fullmatch(r"[a-z0-9_.-]{3,50}", username):
        raise ValueError(
            "El usuario debe tener entre 3 y 50 caracteres (letras, números, punto, guion o guion bajo)."
        )
    if not nombre_completo:
        raise ValueError("El nombre completo es obligatorio.")
    if rol not in ROLES:
        raise ValueError("Rol no válido.")
    _validar_password(password)

    try:
        return execute(
            "INSERT INTO usuarios (username, nombre_completo, password_hash, rol) "
            "VALUES (%s, %s, %s, %s) RETURNING id, username",
            (username, nombre_completo, hash_password(password), rol),
            returning=True,
        )
    except pg_errors.UniqueViolation:
        raise ValueError("Ya existe un usuario con ese nombre de usuario.")


def listar_usuarios():
    return fetch_all(f"SELECT {_CAMPOS_PUBLICOS} FROM usuarios ORDER BY nombre_completo")


def listar_tecnicos():
    """Técnicos activos (para asignar reportes)."""
    return fetch_all(
        "SELECT id, username, nombre_completo FROM usuarios "
        "WHERE rol = %s AND activo = TRUE ORDER BY nombre_completo",
        (ROL_TECNICO,),
    )


def cambiar_estado_activo(usuario_id, activo, actor):
    if not tiene_permiso(actor["rol"], "usuarios.gestionar"):
        raise PermissionError("No tienes permiso para gestionar usuarios.")
    if usuario_id == actor["id"] and not activo:
        raise ValueError("No puedes desactivar tu propia cuenta.")
    execute("UPDATE usuarios SET activo = %s WHERE id = %s", (activo, usuario_id))


def cambiar_password(usuario_id, nueva_password, actor):
    """El administrador puede cambiar cualquier contraseña; los demás solo la propia."""
    if actor["rol"] != ROL_ADMIN and actor["id"] != usuario_id:
        raise PermissionError("No puedes cambiar la contraseña de otro usuario.")
    _validar_password(nueva_password)
    execute(
        "UPDATE usuarios SET password_hash = %s WHERE id = %s",
        (hash_password(nueva_password), usuario_id),
    )


def asegurar_admin_inicial():
    """Si la tabla de usuarios está vacía, crea admin / admin123."""
    fila = fetch_one("SELECT COUNT(*) AS total FROM usuarios")
    if fila and fila["total"] == 0:
        crear_usuario("admin", "Administrador del Sistema", "admin123", ROL_ADMIN)
