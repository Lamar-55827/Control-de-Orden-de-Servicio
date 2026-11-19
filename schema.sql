-- =====================================================================
--  Sistema de Gestión de Reportes y Servicios - Dryg Tools
--  Esquema PostgreSQL / Supabase
--  Ejecutar completo en el editor SQL de Supabase.
-- =====================================================================

-- Necesario para generar el hash bcrypt del usuario admin inicial
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------
-- USUARIOS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    nombre_completo VARCHAR(120) NOT NULL,
    password_hash   TEXT         NOT NULL,
    rol             VARCHAR(20)  NOT NULL
                    CHECK (rol IN ('VENDEDOR', 'TECNICO', 'ADMINISTRADOR')),
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- CLIENTES
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    empresa     VARCHAR(150),
    telefono    VARCHAR(30)  NOT NULL,
    email       VARCHAR(150),
    rfc         VARCHAR(20),
    direccion   TEXT,
    notas       TEXT,
    creado_por  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clientes_nombre  ON clientes (nombre);
CREATE INDEX IF NOT EXISTS idx_clientes_empresa ON clientes (empresa);

-- ---------------------------------------------------------------------
-- REPORTES / ÓRDENES DE SERVICIO (folio automático DRYG-000001)
-- ---------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS reportes_folio_seq START 1;

CREATE TABLE IF NOT EXISTS reportes (
    id                   SERIAL PRIMARY KEY,
    folio                VARCHAR(20) NOT NULL UNIQUE
                         DEFAULT ('DRYG-' || LPAD(nextval('reportes_folio_seq')::TEXT, 6, '0')),
    cliente_id           INTEGER NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    creado_por           INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    tecnico_id           INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo_servicio        VARCHAR(40)  NOT NULL,
    equipo               VARCHAR(150) NOT NULL,
    marca                VARCHAR(80),
    modelo               VARCHAR(80),
    numero_serie         VARCHAR(80),
    descripcion_problema TEXT NOT NULL,
    diagnostico          TEXT,
    estado               VARCHAR(30) NOT NULL DEFAULT 'Recibido'
                         CHECK (estado IN ('Recibido', 'En Diagnóstico', 'En Reparación',
                                           'Esperando Refacciones', 'Listo para Entrega',
                                           'Entregado', 'Cancelado')),
    prioridad            VARCHAR(10) NOT NULL DEFAULT 'Media'
                         CHECK (prioridad IN ('Baja', 'Media', 'Alta', 'Urgente')),
    creado_en            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reportes_estado     ON reportes (estado);
CREATE INDEX IF NOT EXISTS idx_reportes_cliente    ON reportes (cliente_id);
CREATE INDEX IF NOT EXISTS idx_reportes_creado_por ON reportes (creado_por);
CREATE INDEX IF NOT EXISTS idx_reportes_tecnico    ON reportes (tecnico_id);

-- ---------------------------------------------------------------------
-- EVIDENCIAS (archivos adjuntos a un reporte)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidencias (
    id              SERIAL PRIMARY KEY,
    reporte_id      INTEGER NOT NULL REFERENCES reportes(id) ON DELETE CASCADE,
    nombre_archivo  VARCHAR(255) NOT NULL,
    tipo_mime       VARCHAR(100),
    tamano_bytes    INTEGER NOT NULL,
    archivo         BYTEA   NOT NULL,
    descripcion     TEXT,
    subido_por      INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidencias_reporte ON evidencias (reporte_id);

-- ---------------------------------------------------------------------
-- HISTORIAL DE ESTADOS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historial (
    id              SERIAL PRIMARY KEY,
    reporte_id      INTEGER NOT NULL REFERENCES reportes(id) ON DELETE CASCADE,
    usuario_id      INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    estado_anterior VARCHAR(30),
    estado_nuevo    VARCHAR(30) NOT NULL,
    comentario      TEXT,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_historial_reporte ON historial (reporte_id);

-- ---------------------------------------------------------------------
-- SEGURIDAD (Supabase): bloquea el acceso por la API pública (anon key).
-- La aplicación se conecta directamente con el usuario postgres, que
-- ignora RLS, por lo que el sistema sigue funcionando normalmente.
-- ---------------------------------------------------------------------
ALTER TABLE usuarios   ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE reportes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE historial  ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------
-- USUARIO ADMINISTRADOR INICIAL  (usuario: admin / contraseña: admin123)
-- El hash es bcrypt (compatible con la librería bcrypt de Python).
-- ¡CAMBIA LA CONTRASEÑA después del primer ingreso!
-- ---------------------------------------------------------------------
INSERT INTO usuarios (username, nombre_completo, password_hash, rol)
VALUES ('admin', 'Administrador del Sistema', crypt('admin123', gen_salt('bf', 12)), 'ADMINISTRADOR')
ON CONFLICT (username) DO NOTHING;
