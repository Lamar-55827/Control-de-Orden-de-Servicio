"""Reportes / órdenes de servicio: creación, consulta por rol, estados y evidencias."""

from psycopg2 import Binary
from psycopg2.extras import RealDictCursor

from config_settings import (
    ESTADOS,
    ESTADOS_FINALES,
    MAX_EVIDENCIA_MB,
    PRIORIDADES,
    ROL_ADMIN,
    ROL_TECNICO,
    ROL_VENDEDOR,
    TIPOS_SERVICIO,
    tiene_permiso,
)
from db_connection import execute, fetch_all, fetch_one, get_connection

_BASE_SELECT = (
    "SELECT r.*, c.nombre AS cliente_nombre, c.empresa AS cliente_empresa, "
    "u.nombre_completo AS creado_por_nombre, t.nombre_completo AS tecnico_nombre "
    "FROM reportes r "
    "JOIN clientes c ON c.id = r.cliente_id "
    "JOIN usuarios u ON u.id = r.creado_por "
    "LEFT JOIN usuarios t ON t.id = r.tecnico_id "
)


# ---------------------------------------------------------------------------
# Reglas de visibilidad y permisos (lógica de roles)
# ---------------------------------------------------------------------------
def _filtro_rol(usuario, alias="r"):
    """Devuelve (condicion_sql, parametros) según el rol del usuario."""
    rol = usuario["rol"]
    uid = usuario["id"]

    if rol == ROL_ADMIN:
        return "TRUE", ()
    if rol == ROL_TECNICO:
        return (
            f"({alias}.tecnico_id = %s OR {alias}.tecnico_id IS NULL OR {alias}.creado_por = %s)",
            (uid, uid),
        )
    if rol == ROL_VENDEDOR:
        return f"{alias}.creado_por = %s", (uid,)
    return "FALSE", ()


def puede_cambiar_estado(usuario, reporte, nuevo_estado):
    """Reglas por rol para cambiar el estado de un reporte."""
    if nuevo_estado not in ESTADOS or nuevo_estado == reporte["estado"]:
        return False

    rol = usuario["rol"]

    if rol == ROL_ADMIN:
        return True

    # Los reportes cerrados solo los reabre un administrador
    if reporte["estado"] in ESTADOS_FINALES:
        return False

    if rol == ROL_TECNICO:
        return reporte["tecnico_id"] in (None, usuario["id"])

    if rol == ROL_VENDEDOR:
        return (
            nuevo_estado == "Cancelado"
            and reporte["creado_por"] == usuario["id"]
            and reporte["estado"] == "Recibido"
        )

    return False


def estados_permitidos(usuario, reporte):
    return [e for e in ESTADOS if puede_cambiar_estado(usuario, reporte, e)]


# ---------------------------------------------------------------------------
# Creación
# ---------------------------------------------------------------------------
def crear_reporte(datos, usuario):
    """Crea un reporte con folio automático y registra el primer evento del historial."""
    if not tiene_permiso(usuario["rol"], "reportes.crear"):
        raise PermissionError("No tienes permiso para crear reportes.")

    cliente_id = datos.get("cliente_id")
    equipo = (datos.get("equipo") or "").strip()
    descripcion = (datos.get("descripcion_problema") or "").strip()
    tipo = datos.get("tipo_servicio")
    prioridad = datos.get("prioridad") or "Media"

    if not cliente_id:
        raise ValueError("Selecciona un cliente.")
    if not equipo:
        raise ValueError("El equipo o herramienta es obligatorio.")
    if not descripcion:
        raise ValueError("La descripción del problema es obligatoria.")
    if tipo not in TIPOS_SERVICIO:
        raise ValueError("Tipo de servicio no válido.")
    if prioridad not in PRIORIDADES:
        raise ValueError("Prioridad no válida.")

    # Solo el administrador asigna técnico; un técnico se asigna a sí mismo
    tecnico_id = None
    if usuario["rol"] == ROL_ADMIN:
        tecnico_id = datos.get("tecnico_id")
    elif usuario["rol"] == ROL_TECNICO:
        tecnico_id = usuario["id"]

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO reportes (cliente_id, creado_por, tecnico_id, tipo_servicio, equipo, "
                "marca, modelo, numero_serie, descripcion_problema, prioridad) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id, folio",
                (
                    cliente_id,
                    usuario["id"],
                    tecnico_id,
                    tipo,
                    equipo,
                    (datos.get("marca") or "").strip() or None,
                    (datos.get("modelo") or "").strip() or None,
                    (datos.get("numero_serie") or "").strip() or None,
                    descripcion,
                    prioridad,
                ),
            )
            nuevo = dict(cur.fetchone())
            cur.execute(
                "INSERT INTO historial (reporte_id, usuario_id, estado_anterior, estado_nuevo, comentario) "
                "VALUES (%s, %s, NULL, 'Recibido', 'Reporte creado')",
                (nuevo["id"], usuario["id"]),
            )
    return nuevo


# ---------------------------------------------------------------------------
# Consulta (filtrada por rol)
# ---------------------------------------------------------------------------
def listar_reportes(usuario, estados=None, busqueda="", limite=500):
    filtro, params = _filtro_rol(usuario)
    condiciones = [filtro]
    params = list(params)

    if estados:
        condiciones.append("r.estado = ANY(%s)")
        params.append(list(estados))

    if busqueda and busqueda.strip():
        like = f"%{busqueda.strip()}%"
        condiciones.append(
            "(r.folio ILIKE %s OR r.equipo ILIKE %s OR r.numero_serie ILIKE %s "
            "OR c.nombre ILIKE %s OR c.empresa ILIKE %s)"
        )
        params.extend([like] * 5)

    sql = _BASE_SELECT + "WHERE " + " AND ".join(condiciones) + " ORDER BY r.creado_en DESC LIMIT %s"
    params.append(limite)
    return fetch_all(sql, tuple(params))


def obtener_reporte(reporte_id, usuario):
    """Devuelve el reporte solo si el rol del usuario puede verlo."""
    filtro, params = _filtro_rol(usuario)
    return fetch_one(
        _BASE_SELECT + "WHERE r.id = %s AND " + filtro,
        (reporte_id,) + tuple(params),
    )


def estadisticas(usuario):
    """Conteo de reportes por estado (respetando el rol)."""
    filtro, params = _filtro_rol(usuario)
    filas = fetch_all(
        "SELECT r.estado, COUNT(*) AS total FROM reportes r WHERE " + filtro + " GROUP BY r.estado",
        tuple(params),
    )
    return {f["estado"]: f["total"] for f in filas}


# ---------------------------------------------------------------------------
# Cambios de estado y asignación
# ---------------------------------------------------------------------------
def cambiar_estado(reporte_id, nuevo_estado, usuario, comentario="", diagnostico=None):
    if nuevo_estado not in ESTADOS:
        raise ValueError("Estado no válido.")

    reporte = obtener_reporte(reporte_id, usuario)
    if not reporte:
        raise PermissionError("No tienes acceso a este reporte.")
    if not puede_cambiar_estado(usuario, reporte, nuevo_estado):
        raise PermissionError("No tienes permiso para realizar este cambio de estado.")

    diag = (diagnostico or "").strip() or None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE reportes SET estado = %s, diagnostico = COALESCE(%s, diagnostico), "
                "tecnico_id = CASE WHEN %s THEN COALESCE(tecnico_id, %s) ELSE tecnico_id END, "
                "actualizado_en = NOW() WHERE id = %s",
                (nuevo_estado, diag, usuario["rol"] == ROL_TECNICO, usuario["id"], reporte_id),
            )
            cur.execute(
                "INSERT INTO historial (reporte_id, usuario_id, estado_anterior, estado_nuevo, comentario) "
                "VALUES (%s, %s, %s, %s, %s)",
                (reporte_id, usuario["id"], reporte["estado"], nuevo_estado, (comentario or "").strip() or None),
            )


def asignar_tecnico(reporte_id, tecnico_id, usuario):
    if not tiene_permiso(usuario["rol"], "reportes.asignar"):
        raise PermissionError("Solo un administrador puede asignar técnicos.")

    reporte = obtener_reporte(reporte_id, usuario)
    if not reporte:
        raise PermissionError("No tienes acceso a este reporte.")

    tecnico = fetch_one(
        "SELECT nombre_completo FROM usuarios WHERE id = %s AND rol = %s AND activo = TRUE",
        (tecnico_id, ROL_TECNICO),
    )
    if not tecnico:
        raise ValueError("El técnico seleccionado no es válido.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE reportes SET tecnico_id = %s, actualizado_en = NOW() WHERE id = %s",
                (tecnico_id, reporte_id),
            )
            cur.execute(
                "INSERT INTO historial (reporte_id, usuario_id, estado_anterior, estado_nuevo, comentario) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    reporte_id,
                    usuario["id"],
                    reporte["estado"],
                    reporte["estado"],
                    f"Técnico asignado: {tecnico['nombre_completo']}",
                ),
            )


def historial_reporte(reporte_id):
    return fetch_all(
        "SELECT h.*, u.nombre_completo AS usuario_nombre "
        "FROM historial h LEFT JOIN usuarios u ON u.id = h.usuario_id "
        "WHERE h.reporte_id = %s ORDER BY h.creado_en ASC, h.id ASC",
        (reporte_id,),
    )


# ---------------------------------------------------------------------------
# Evidencias
# ---------------------------------------------------------------------------
def agregar_evidencia(reporte_id, usuario, nombre_archivo, tipo_mime, contenido, descripcion=""):
    if not tiene_permiso(usuario["rol"], "reportes.evidencias"):
        raise PermissionError("No tienes permiso para adjuntar evidencias.")
    if not obtener_reporte(reporte_id, usuario):
        raise PermissionError("No tienes acceso a este reporte.")
    if len(contenido) > MAX_EVIDENCIA_MB * 1024 * 1024:
        raise ValueError(f"El archivo '{nombre_archivo}' excede {MAX_EVIDENCIA_MB} MB.")

    execute(
        "INSERT INTO evidencias (reporte_id, nombre_archivo, tipo_mime, tamano_bytes, archivo, "
        "descripcion, subido_por) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            reporte_id,
            nombre_archivo,
            tipo_mime,
            len(contenido),
            Binary(contenido),
            (descripcion or "").strip() or None,
            usuario["id"],
        ),
    )


def listar_evidencias(reporte_id, con_datos=False):
    campos = (
        "e.id, e.nombre_archivo, e.tipo_mime, e.tamano_bytes, e.descripcion, e.creado_en, "
        "u.nombre_completo AS subido_por_nombre"
    )
    if con_datos:
        campos += ", e.archivo"
    filas = fetch_all(
        f"SELECT {campos} FROM evidencias e LEFT JOIN usuarios u ON u.id = e.subido_por "
        "WHERE e.reporte_id = %s ORDER BY e.creado_en ASC, e.id ASC",
        (reporte_id,),
    )
    if con_datos:
        for fila in filas:
            fila["archivo"] = bytes(fila["archivo"])
    return filas
