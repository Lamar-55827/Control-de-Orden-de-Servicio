# Sistema de Gestión de Reportes y Servicios – Dryg Tools

**Especialistas en Herramientas de Torque**

Aplicación web hecha con **Streamlit** y **PostgreSQL / Supabase** para registrar clientes,
levantar órdenes de servicio con folio automático (`DRYG-000001`), dar seguimiento a su estado
y generar reportes en PDF con **ReportLab**.

## Características

- Roles: **Vendedor**, **Técnico** y **Administrador** (validados desde la lógica del código).
- Registro y consulta de clientes para los tres roles.
- Reportes / órdenes de servicio con folio automático, consulta filtrada por rol y cambio de estados con historial.
- Evidencias adjuntas (imágenes / PDF) guardadas en la base de datos.
- PDF del reporte generado con ReportLab.
- Contraseñas cifradas con **bcrypt**.

### Permisos por rol

| Acción                              | Vendedor        | Técnico                  | Administrador |
|-------------------------------------|-----------------|--------------------------|---------------|
| Registrar / consultar clientes      | Sí              | Sí                       | Sí            |
| Editar clientes                     | No              | No                       | Sí            |
| Crear reportes                      | Sí              | Sí (se auto-asigna)      | Sí            |
| Ver reportes                        | Solo los suyos  | Asignados, sin asignar y propios | Todos |
| Cambiar estado                      | Solo cancelar los suyos en "Recibido" | Sí | Sí |
| Asignar técnico                     | No              | No                       | Sí            |
| Gestionar usuarios                  | No              | No                       | Sí            |

## Instalación

1. Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # En Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Crea un proyecto en [Supabase](https://supabase.com) (o usa cualquier PostgreSQL) y ejecuta
   el contenido de `database/schema.sql` en el editor SQL.

3. Crea el archivo `.streamlit/secrets.toml` con la cadena de conexión:

   ```toml
   DATABASE_URL = "postgresql://postgres:TU_PASSWORD@db.xxxxx.supabase.co:5432/postgres"
   ```

   También puedes definir la variable de entorno `DATABASE_URL`.

4. Ejecuta la aplicación:

   ```bash
   streamlit run app.py
   ```

## Acceso inicial

- Usuario: `admin`
- Contraseña: `admin123`

**Cambia esta contraseña inmediatamente** desde el módulo *Usuarios* después del primer ingreso.

## Estructura

```
sistema_dryg_tools/
├── app.py
├── requirements.txt
├── assets/estilos.css
├── config/settings.py
├── database/
│   ├── schema.sql
│   ├── connection.py
│   ├── usuarios.py
│   ├── clientes.py
│   └── reportes.py
├── modules/
│   ├── login.py
│   └── pdf_generator.py
└── .streamlit/config.toml
```

## Identidad visual

| Elemento              | Color     |
|-----------------------|-----------|
| Header superior       | `#D32F2F` |
| Sidebar               | `#1E272C` |
| Encabezados de módulo | `#003B73` |
