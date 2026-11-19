"""Conexión a PostgreSQL / Supabase y helpers de consulta."""

from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from config_settings import get_database_url


@contextmanager
def get_connection():
    """Abre una conexión; hace commit al salir o rollback si hay error."""
    conn = psycopg2.connect(get_database_url(), connect_timeout=10)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query, params=None):
    """Ejecuta un SELECT y devuelve una lista de diccionarios."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            return [dict(fila) for fila in cur.fetchall()]


def fetch_one(query, params=None):
    """Ejecuta un SELECT y devuelve un diccionario o None."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            fila = cur.fetchone()
            return dict(fila) if fila else None


def execute(query, params=None, returning=False):
    """Ejecuta INSERT/UPDATE/DELETE.

    Con returning=True devuelve la fila de RETURNING como diccionario;
    en caso contrario devuelve el número de filas afectadas.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if returning:
                fila = cur.fetchone()
                return dict(fila) if fila else None
            return cur.rowcount


def probar_conexion():
    """Devuelve True si la base de datos responde."""
    fila = fetch_one("SELECT 1 AS ok")
    return bool(fila and fila["ok"] == 1)
