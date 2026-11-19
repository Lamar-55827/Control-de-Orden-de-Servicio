"""Registro y consulta de clientes (Vendedor, Técnico y Administrador)."""

from config_settings import tiene_permiso
from db_connection import execute, fetch_all, fetch_one


def _limpiar(valor):
    valor = (valor or "").strip()
    return valor or None


def _validar(datos):
    nombre = (datos.get("nombre") or "").strip()
    telefono = (datos.get("telefono") or "").strip()
    email = _limpiar(datos.get("email"))

    if not nombre:
        raise ValueError("El nombre del cliente es obligatorio.")
    if not telefono:
        raise ValueError("El teléfono es obligatorio.")
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        raise ValueError("El correo electrónico no es válido.")

    return (
        nombre,
        _limpiar(datos.get("empresa")),
        telefono,
        email,
        _limpiar(datos.get("rfc")),
        _limpiar(datos.get("direccion")),
        _limpiar(datos.get("notas")),
    )


def crear_cliente(datos, usuario):
    if not tiene_permiso(usuario["rol"], "clientes.crear"):
        raise PermissionError("No tienes permiso para registrar clientes.")

    valores = _validar(datos)
    return execute(
        "INSERT INTO clientes (nombre, empresa, telefono, email, rfc, direccion, notas, creado_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id, nombre",
        valores + (usuario["id"],),
        returning=True,
    )


def listar_clientes(busqueda="", limite=1000):
    sql = (
        "SELECT c.id, c.nombre, c.empresa, c.telefono, c.email, c.rfc, c.direccion, c.notas, "
        "c.creado_en, u.nombre_completo AS creado_por_nombre "
        "FROM clientes c LEFT JOIN usuarios u ON u.id = c.creado_por "
    )
    params = []
    if busqueda and busqueda.strip():
        like = f"%{busqueda.strip()}%"
        sql += (
            "WHERE c.nombre ILIKE %s OR c.empresa ILIKE %s OR c.telefono ILIKE %s "
            "OR c.email ILIKE %s OR c.rfc ILIKE %s "
        )
        params.extend([like] * 5)
    sql += "ORDER BY c.nombre LIMIT %s"
    params.append(limite)
    return fetch_all(sql, tuple(params))


def obtener_cliente(cliente_id):
    return fetch_one("SELECT * FROM clientes WHERE id = %s", (cliente_id,))


def actualizar_cliente(cliente_id, datos, usuario):
    if not tiene_permiso(usuario["rol"], "clientes.editar"):
        raise PermissionError("Solo un administrador puede editar clientes.")

    valores = _validar(datos)
    execute(
        "UPDATE clientes SET nombre = %s, empresa = %s, telefono = %s, email = %s, "
        "rfc = %s, direccion = %s, notas = %s WHERE id = %s",
        valores + (cliente_id,),
    )


def contar_clientes():
    fila = fetch_one("SELECT COUNT(*) AS total FROM clientes")
    return fila["total"] if fila else 0
