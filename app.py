"""Sistema de Gestión de Reportes y Servicios - Dryg Tools

Ejecutar con:  streamlit run app.py
"""

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from config.settings import (
    APP_NOMBRE,
    EMPRESA,
    ESLOGAN,
    ESTADO_COLORES,
    ESTADOS,
    MENU_CLIENTES,
    MENU_INICIO,
    MENU_POR_ROL,
    MENU_REPORTES,
    MENU_USUARIOS,
    PRIORIDADES,
    ROL_ADMIN,
    ROL_ETIQUETAS,
    ROLES,
    TIPOS_SERVICIO,
    tiene_permiso,
)
from database import clientes as db_clientes
from database import reportes as db_reportes
from database import usuarios as db_usuarios
from modules.login import cerrar_sesion, render_login
from modules.pdf_generator import generar_pdf_reporte

BASE_DIR = Path(__file__).parent

st.set_page_config(
    page_title=f"{EMPRESA} | Gestión de Servicios",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Utilidades de interfaz
# ---------------------------------------------------------------------------
def cargar_css():
    ruta = BASE_DIR / "assets" / "estilos.css"
    if ruta.exists():
        st.markdown(f"<style>{ruta.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def fmt_fecha(valor):
    if not valor:
        return "—"
    try:
        return valor.astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)


def encabezado_top():
    st.markdown(
        f'<div class="top-header"><div class="top-marca">🔧 {html.escape(EMPRESA.upper())}</div>'
        f'<div class="top-eslogan">{html.escape(ESLOGAN)}</div></div>',
        unsafe_allow_html=True,
    )


def encabezado_modulo(titulo, subtitulo=""):
    sub = f"<small>{html.escape(subtitulo)}</small>" if subtitulo else ""
    st.markdown(
        f'<div class="modulo-header">{html.escape(titulo)}{sub}</div>',
        unsafe_allow_html=True,
    )


def subtitulo(texto):
    st.markdown(f'<div class="subtitulo-azul">{html.escape(texto)}</div>', unsafe_allow_html=True)


def badge_estado(estado):
    color = ESTADO_COLORES.get(estado, "#607D8B")
    return f'<span class="badge-estado" style="background:{color}">{html.escape(str(estado))}</span>'


def flash(mensaje, tipo="success"):
    """Guarda un mensaje para mostrarlo después de un st.rerun()."""
    st.session_state["_flash"] = (tipo, mensaje)


def mostrar_flash():
    dato = st.session_state.pop("_flash", None)
    if dato:
        tipo, mensaje = dato
        getattr(st, tipo, st.info)(mensaje)


def mostrar_error(error):
    if isinstance(error, (ValueError, PermissionError)):
        st.error(str(error))
    else:
        st.error("Ocurrió un error inesperado al procesar la operación.")
        st.caption(f"Detalle técnico: {error}")


@st.cache_resource(show_spinner=False)
def _inicializar_bd():
    db_usuarios.asegurar_admin_inicial()
    return True


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar(usuario):
    with st.sidebar:
        st.markdown(
            f'<div class="sidebar-marca">🔧 {html.escape(EMPRESA)}</div>'
            f'<div class="sidebar-eslogan">{html.escape(ESLOGAN)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="usuario-box"><div class="usuario-nombre">{html.escape(usuario["nombre_completo"])}</div>'
            f'<div class="usuario-rol">{html.escape(ROL_ETIQUETAS.get(usuario["rol"], usuario["rol"]))}</div>'
            f'<div class="estado-linea"><span class="punto-verde"></span>En Línea</div></div>',
            unsafe_allow_html=True,
        )
        seleccion = st.radio(
            "Navegación",
            MENU_POR_ROL.get(usuario["rol"], [MENU_INICIO]),
            label_visibility="collapsed",
            key="menu",
        )
        st.divider()
        if st.button("🚪 Cerrar sesión"):
            cerrar_sesion()
            st.rerun()
    return seleccion


# ---------------------------------------------------------------------------
# Módulo: Inicio
# ---------------------------------------------------------------------------
def pagina_inicio(usuario):
    encabezado_modulo("Panel de Control", f"Bienvenido, {usuario['nombre_completo']}")

    try:
        stats = db_reportes.estadisticas(usuario)
        total = sum(stats.values())
        columnas = st.columns(5)
        columnas[0].metric("Total de reportes", total)
        columnas[1].metric("Recibidos", stats.get("Recibido", 0))
        columnas[2].metric("En diagnóstico", stats.get("En Diagnóstico", 0))
        columnas[3].metric("En reparación", stats.get("En Reparación", 0))
        columnas[4].metric("Listos para entrega", stats.get("Listo para Entrega", 0))

        subtitulo("Últimos reportes")
        ultimos = db_reportes.listar_reportes(usuario, limite=10)
        if ultimos:
            df = pd.DataFrame(
                [
                    {
                        "Folio": r["folio"],
                        "Cliente": r["cliente_nombre"],
                        "Equipo": r["equipo"],
                        "Estado": r["estado"],
                        "Prioridad": r["prioridad"],
                        "Fecha": fmt_fecha(r["creado_en"]),
                    }
                    for r in ultimos
                ]
            )
            st.dataframe(df, hide_index=True)
        else:
            st.info("Aún no hay reportes registrados.")

        subtitulo("Clientes")
        st.metric("Clientes registrados", db_clientes.contar_clientes())
    except Exception as error:
        mostrar_error(error)


# ---------------------------------------------------------------------------
# Módulo: Clientes
# ---------------------------------------------------------------------------
def _form_cliente(clave, valores=None, etiqueta_boton="Guardar cliente", limpiar=True):
    """Dibuja el formulario de cliente. Devuelve (enviado, datos)."""
    v = valores or {}
    with st.form(clave, clear_on_submit=limpiar):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre del contacto *", value=v.get("nombre") or "")
        empresa = c2.text_input("Empresa", value=v.get("empresa") or "")
        telefono = c1.text_input("Teléfono *", value=v.get("telefono") or "")
        email = c2.text_input("Correo electrónico", value=v.get("email") or "")
        rfc = c1.text_input("RFC", value=v.get("rfc") or "")
        direccion = c2.text_input("Dirección", value=v.get("direccion") or "")
        notas = st.text_area("Notas", value=v.get("notas") or "")
        enviado = st.form_submit_button(etiqueta_boton, type="primary")
    datos = {
        "nombre": nombre,
        "empresa": empresa,
        "telefono": telefono,
        "email": email,
        "rfc": rfc,
        "direccion": direccion,
        "notas": notas,
    }
    return enviado, datos


def pagina_clientes(usuario):
    if not tiene_permiso(usuario["rol"], "clientes.ver"):
        st.error("No tienes permiso para acceder a este módulo.")
        return

    encabezado_modulo("Registro de Clientes", "Registra y consulta clientes")
    mostrar_flash()

    pestanas = ["➕ Registrar cliente", "🔎 Consultar clientes"]
    tab_registro, tab_consulta = st.tabs(pestanas)

    with tab_registro:
        if not tiene_permiso(usuario["rol"], "clientes.crear"):
            st.warning("Tu rol no puede registrar clientes.")
        else:
            enviado, datos = _form_cliente("form_cliente_nuevo")
            if enviado:
                try:
                    nuevo = db_clientes.crear_cliente(datos, usuario)
                    flash(f"Cliente «{nuevo['nombre']}» registrado correctamente.")
                    st.rerun()
                except Exception as error:
                    mostrar_error(error)

    with tab_consulta:
        busqueda = st.text_input("Buscar (nombre, empresa, teléfono, correo o RFC)", key="busqueda_clientes")
        try:
            clientes = db_clientes.listar_clientes(busqueda)
        except Exception as error:
            mostrar_error(error)
            return

        if not clientes:
            st.info("No se encontraron clientes.")
            return

        st.caption(f"{len(clientes)} cliente(s)")
        df = pd.DataFrame(
            [
                {
                    "ID": c["id"],
                    "Nombre": c["nombre"],
                    "Empresa": c["empresa"] or "",
                    "Teléfono": c["telefono"],
                    "Correo": c["email"] or "",
                    "RFC": c["rfc"] or "",
                    "Registrado por": c["creado_por_nombre"] or "",
                    "Fecha": fmt_fecha(c["creado_en"]),
                }
                for c in clientes
            ]
        )
        st.dataframe(df, hide_index=True)

        if tiene_permiso(usuario["rol"], "clientes.editar"):
            subtitulo("Editar cliente (solo administrador)")
            opciones = {f"{c['nombre']} — {c['empresa'] or 's/empresa'} (#{c['id']})": c for c in clientes}
            etiqueta = st.selectbox("Selecciona un cliente", list(opciones), key="sel_editar_cliente")
            elegido = opciones[etiqueta]
            enviado, datos = _form_cliente(
                f"form_cliente_editar_{elegido['id']}",
                valores=elegido,
                etiqueta_boton="Actualizar cliente",
                limpiar=False,
            )
            if enviado:
                try:
                    db_clientes.actualizar_cliente(elegido["id"], datos, usuario)
                    flash("Cliente actualizado correctamente.")
                    st.rerun()
                except Exception as error:
                    mostrar_error(error)


# ---------------------------------------------------------------------------
# Módulo: Reportes de servicio
# ---------------------------------------------------------------------------
def _form_nuevo_reporte(usuario):
    try:
        clientes = db_clientes.listar_clientes()
        tecnicos = db_usuarios.listar_tecnicos() if usuario["rol"] == ROL_ADMIN else []
    except Exception as error:
        mostrar_error(error)
        return

    if not clientes:
        st.info("Primero registra un cliente en el módulo Clientes.")
        return

    opciones_cliente = {
        f"{c['nombre']}" + (f" — {c['empresa']}" if c["empresa"] else "") + f" (#{c['id']})": c["id"]
        for c in clientes
    }
    opciones_tecnico = {"Sin asignar": None}
    opciones_tecnico.update({t["nombre_completo"]: t["id"] for t in tecnicos})

    with st.form("form_reporte_nuevo", clear_on_submit=True):
        cliente_label = st.selectbox("Cliente *", list(opciones_cliente))
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo de servicio *", TIPOS_SERVICIO)
        prioridad = c2.selectbox("Prioridad", PRIORIDADES, index=1)
        equipo = c1.text_input("Equipo / Herramienta *")
        marca = c2.text_input("Marca")
        modelo = c1.text_input("Modelo")
        serie = c2.text_input("Número de serie")
        tecnico_label = None
        if usuario["rol"] == ROL_ADMIN:
            tecnico_label = st.selectbox("Técnico asignado", list(opciones_tecnico))
        descripcion = st.text_area("Descripción del problema *", height=120)
        enviado = st.form_submit_button("Crear reporte", type="primary")

    if enviado:
        try:
            nuevo = db_reportes.crear_reporte(
                {
                    "cliente_id": opciones_cliente[cliente_label],
                    "tipo_servicio": tipo,
                    "prioridad": prioridad,
                    "equipo": equipo,
                    "marca": marca,
                    "modelo": modelo,
                    "numero_serie": serie,
                    "descripcion_problema": descripcion,
                    "tecnico_id": opciones_tecnico.get(tecnico_label) if tecnico_label else None,
                },
                usuario,
            )
            flash(f"Reporte creado con folio {nuevo['folio']}.")
            st.rerun()
        except Exception as error:
            mostrar_error(error)


def _detalle_reporte(usuario, reporte_id):
    reporte = db_reportes.obtener_reporte(reporte_id, usuario)
    if not reporte:
        st.warning("No se encontró el reporte o no tienes acceso a él.")
        return

    cliente = db_clientes.obtener_cliente(reporte["cliente_id"]) or {}
    historial = db_reportes.historial_reporte(reporte_id)
    evidencias = db_reportes.listar_evidencias(reporte_id, con_datos=True)

    subtitulo(f"Detalle del reporte {reporte['folio']}")
    st.markdown(badge_estado(reporte["estado"]), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Cliente:** {reporte['cliente_nombre']}")
        st.markdown(f"**Empresa:** {reporte['cliente_empresa'] or '—'}")
        st.markdown(f"**Teléfono:** {cliente.get('telefono') or '—'}")
        st.markdown(f"**Registrado por:** {reporte['creado_por_nombre']}")
        st.markdown(f"**Técnico:** {reporte['tecnico_nombre'] or 'Sin asignar'}")
    with c2:
        st.markdown(f"**Tipo de servicio:** {reporte['tipo_servicio']}")
        st.markdown(f"**Equipo:** {reporte['equipo']}")
        st.markdown(f"**Marca / Modelo:** {reporte['marca'] or '—'} / {reporte['modelo'] or '—'}")
        st.markdown(f"**Número de serie:** {reporte['numero_serie'] or '—'}")
        st.markdown(f"**Prioridad:** {reporte['prioridad']}")

    st.markdown("**Descripción del problema**")
    st.info(reporte["descripcion_problema"])
    st.markdown("**Diagnóstico / trabajo realizado**")
    st.write(reporte["diagnostico"] or "—")

    # --- PDF ---
    if tiene_permiso(usuario["rol"], "reportes.pdf"):
        try:
            pdf = generar_pdf_reporte(reporte, cliente, historial, evidencias)
            st.download_button(
                "📄 Descargar PDF",
                data=pdf,
                file_name=f"{reporte['folio']}.pdf",
                mime="application/pdf",
                key=f"pdf_{reporte_id}",
            )
        except Exception as error:
            st.error(f"No se pudo generar el PDF: {error}")

    # --- Cambio de estado ---
    permitidos = db_reportes.estados_permitidos(usuario, reporte)
    if permitidos:
        subtitulo("Cambiar estado")
        with st.form(f"form_estado_{reporte_id}", clear_on_submit=True):
            nuevo_estado = st.selectbox("Nuevo estado", permitidos)
            diagnostico = None
            if usuario["rol"] != "VENDEDOR":
                diagnostico = st.text_area(
                    "Diagnóstico / trabajo realizado (opcional)",
                    value=reporte["diagnostico"] or "",
                )
            comentario = st.text_input("Comentario")
            enviado = st.form_submit_button("Actualizar estado", type="primary")
        if enviado:
            try:
                db_reportes.cambiar_estado(reporte_id, nuevo_estado, usuario, comentario, diagnostico)
                flash(f"Estado actualizado a «{nuevo_estado}».")
                st.rerun()
            except Exception as error:
                mostrar_error(error)

    # --- Asignación de técnico ---
    if tiene_permiso(usuario["rol"], "reportes.asignar"):
        try:
            tecnicos = db_usuarios.listar_tecnicos()
        except Exception:
            tecnicos = []
        if tecnicos:
            subtitulo("Asignar técnico")
            opciones = {t["nombre_completo"]: t["id"] for t in tecnicos}
            with st.form(f"form_asignar_{reporte_id}"):
                nombre = st.selectbox("Técnico", list(opciones))
                enviado = st.form_submit_button("Asignar")
            if enviado:
                try:
                    db_reportes.asignar_tecnico(reporte_id, opciones[nombre], usuario)
                    flash(f"Técnico asignado: {nombre}.")
                    st.rerun()
                except Exception as error:
                    mostrar_error(error)

    # --- Evidencias ---
    subtitulo("Evidencias")
    if evidencias:
        for ev in evidencias:
            etiqueta = f"{ev['nombre_archivo']} — {ev['descripcion'] or 'sin descripción'}"
            if (ev["tipo_mime"] or "").startswith("image/"):
                st.image(ev["archivo"], caption=etiqueta, width=320)
            else:
                st.download_button(
                    f"📎 {etiqueta}",
                    data=ev["archivo"],
                    file_name=ev["nombre_archivo"],
                    mime=ev["tipo_mime"] or "application/octet-stream",
                    key=f"evid_{ev['id']}",
                )
    else:
        st.caption("Sin evidencias adjuntas.")

    if tiene_permiso(usuario["rol"], "reportes.evidencias"):
        with st.form(f"form_evidencia_{reporte_id}", clear_on_submit=True):
            archivos = st.file_uploader(
                "Adjuntar evidencias",
                accept_multiple_files=True,
                type=["png", "jpg", "jpeg", "webp", "pdf"],
            )
            descripcion = st.text_input("Descripción")
            enviado = st.form_submit_button("Subir evidencias")
        if enviado:
            if not archivos:
                st.warning("Selecciona al menos un archivo.")
            else:
                try:
                    for archivo in archivos:
                        db_reportes.agregar_evidencia(
                            reporte_id,
                            usuario,
                            archivo.name,
                            archivo.type,
                            archivo.getvalue(),
                            descripcion,
                        )
                    flash(f"{len(archivos)} evidencia(s) cargada(s).")
                    st.rerun()
                except Exception as error:
                    mostrar_error(error)

    # --- Historial ---
    subtitulo("Historial")
    if historial:
        df = pd.DataFrame(
            [
                {
                    "Fecha": fmt_fecha(h["creado_en"]),
                    "Usuario": h["usuario_nombre"] or "—",
                    "De": h["estado_anterior"] or "—",
                    "A": h["estado_nuevo"],
                    "Comentario": h["comentario"] or "",
                }
                for h in historial
            ]
        )
        st.dataframe(df, hide_index=True)


def pagina_reportes(usuario):
    if not tiene_permiso(usuario["rol"], "reportes.ver"):
        st.error("No tienes permiso para acceder a este módulo.")
        return

    encabezado_modulo("Reportes de Servicio", "Órdenes de servicio con folio automático")
    mostrar_flash()

    tab_nuevo, tab_consulta = st.tabs(["➕ Nuevo reporte", "📋 Consultar y gestionar"])

    with tab_nuevo:
        if tiene_permiso(usuario["rol"], "reportes.crear"):
            _form_nuevo_reporte(usuario)
        else:
            st.warning("Tu rol no puede crear reportes.")

    with tab_consulta:
        f1, f2 = st.columns([2, 3])
        estados = f1.multiselect("Filtrar por estado", ESTADOS, key="filtro_estados")
        busqueda = f2.text_input("Buscar (folio, cliente, equipo o serie)", key="busqueda_reportes")

        try:
            reportes = db_reportes.listar_reportes(usuario, estados=estados, busqueda=busqueda)
        except Exception as error:
            mostrar_error(error)
            return

        if usuario["rol"] == "VENDEDOR":
            st.caption("Se muestran únicamente los reportes que tú registraste.")
        elif usuario["rol"] == "TECNICO":
            st.caption("Se muestran tus reportes asignados, los registrados por ti y los que aún no tienen técnico.")

        if not reportes:
            st.info("No se encontraron reportes con esos filtros.")
            return

        st.caption(f"{len(reportes)} reporte(s)")
        df = pd.DataFrame(
            [
                {
                    "Folio": r["folio"],
                    "Cliente": r["cliente_nombre"],
                    "Equipo": f"{r['equipo']} {r['marca'] or ''}".strip(),
                    "Tipo": r["tipo_servicio"],
                    "Estado": r["estado"],
                    "Prioridad": r["prioridad"],
                    "Técnico": r["tecnico_nombre"] or "Sin asignar",
                    "Registrado por": r["creado_por_nombre"],
                    "Fecha": fmt_fecha(r["creado_en"]),
                }
                for r in reportes
            ]
        )
        st.dataframe(df, hide_index=True)

        opciones = {f"{r['folio']} — {r['cliente_nombre']} — {r['equipo']}": r["id"] for r in reportes}
        etiqueta = st.selectbox("Selecciona un reporte para ver el detalle", list(opciones), key="sel_reporte")
        try:
            _detalle_reporte(usuario, opciones[etiqueta])
        except Exception as error:
            mostrar_error(error)


# ---------------------------------------------------------------------------
# Módulo: Usuarios (solo administrador)
# ---------------------------------------------------------------------------
def pagina_usuarios(usuario):
    if not tiene_permiso(usuario["rol"], "usuarios.gestionar"):
        st.error("No tienes permiso para acceder a este módulo.")
        return

    encabezado_modulo("Gestión de Usuarios", "Alta de usuarios, roles y contraseñas")
    mostrar_flash()

    tab_nuevo, tab_lista = st.tabs(["➕ Nuevo usuario", "👥 Usuarios del sistema"])

    with tab_nuevo:
        with st.form("form_usuario_nuevo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            username = c1.text_input("Usuario *")
            nombre = c2.text_input("Nombre completo *")
            password = c1.text_input("Contraseña * (mínimo 6 caracteres)", type="password")
            rol = c2.selectbox("Rol *", ROLES, format_func=lambda r: ROL_ETIQUETAS[r])
            enviado = st.form_submit_button("Crear usuario", type="primary")
        if enviado:
            try:
                db_usuarios.crear_usuario(username, nombre, password, rol, actor=usuario)
                flash(f"Usuario «{username.strip().lower()}» creado correctamente.")
                st.rerun()
            except Exception as error:
                mostrar_error(error)

    with tab_lista:
        try:
            lista = db_usuarios.listar_usuarios()
        except Exception as error:
            mostrar_error(error)
            return

        df = pd.DataFrame(
            [
                {
                    "Usuario": u["username"],
                    "Nombre": u["nombre_completo"],
                    "Rol": ROL_ETIQUETAS.get(u["rol"], u["rol"]),
                    "Activo": "Sí" if u["activo"] else "No",
                    "Creado": fmt_fecha(u["creado_en"]),
                }
                for u in lista
            ]
        )
        st.dataframe(df, hide_index=True)

        subtitulo("Administrar usuario")
        opciones = {f"{u['nombre_completo']} ({u['username']})": u for u in lista}
        etiqueta = st.selectbox("Selecciona un usuario", list(opciones), key="sel_usuario")
        elegido = opciones[etiqueta]

        accion = "Desactivar" if elegido["activo"] else "Activar"
        resultado = "desactivado" if elegido["activo"] else "activado"
        if st.button(f"{accion} usuario", key=f"toggle_{elegido['id']}"):
            try:
                db_usuarios.cambiar_estado_activo(elegido["id"], not elegido["activo"], usuario)
                flash(f"Usuario {resultado} correctamente.")
                st.rerun()
            except Exception as error:
                mostrar_error(error)

        with st.form(f"form_password_{elegido['id']}", clear_on_submit=True):
            nueva = st.text_input("Nueva contraseña", type="password")
            enviado = st.form_submit_button("Cambiar contraseña")
        if enviado:
            try:
                db_usuarios.cambiar_password(elegido["id"], nueva, usuario)
                flash("Contraseña actualizada correctamente.")
                st.rerun()
            except Exception as error:
                mostrar_error(error)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
PAGINAS = {
    MENU_INICIO: pagina_inicio,
    MENU_CLIENTES: pagina_clientes,
    MENU_REPORTES: pagina_reportes,
    MENU_USUARIOS: pagina_usuarios,
}


def main():
    cargar_css()

    try:
        _inicializar_bd()
    except Exception:
        pass  # El login mostrará el detalle del error de conexión

    encabezado_top()

    usuario = st.session_state.get("usuario")
    if not usuario:
        render_login()
        return

    seleccion = render_sidebar(usuario)

    # Validación de rol desde la lógica: solo se permiten las páginas de su menú
    if seleccion not in MENU_POR_ROL.get(usuario["rol"], []):
        st.error("No tienes permiso para acceder a este módulo.")
        return

    PAGINAS[seleccion](usuario)


main()
