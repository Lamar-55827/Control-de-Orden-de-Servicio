"""Generación del PDF de una orden de servicio con ReportLab."""

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config_settings import COLOR_HEADER, COLOR_MODULO, COLOR_SIDEBAR, EMPRESA, ESLOGAN, ESTADO_COLORES

ROJO = colors.HexColor(COLOR_HEADER)
AZUL = colors.HexColor(COLOR_MODULO)
GRIS_OSCURO = colors.HexColor(COLOR_SIDEBAR)
GRIS_CLARO = colors.HexColor("#F4F6F8")
GRIS_LINEA = colors.HexColor("#CFD8DC")

ANCHO_UTIL = letter[0] - 4 * cm
MAX_IMAGENES = 6


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _txt(valor):
    """Texto seguro para Paragraph (escapa XML y respeta saltos de línea)."""
    if valor is None or str(valor).strip() == "":
        return "—"
    return escape(str(valor)).replace("\n", "<br/>")


def _fecha(valor):
    if not valor:
        return "—"
    try:
        return valor.astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        try:
            return valor.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(valor)


def _estilos():
    base = getSampleStyleSheet()
    return {
        "normal": ParagraphStyle("normal", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=GRIS_OSCURO),
        "label": ParagraphStyle("label", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=AZUL),
        "seccion": ParagraphStyle("seccion", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.white),
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=AZUL, alignment=0),
        "pequeno": ParagraphStyle("pequeno", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8, leading=10, textColor=colors.HexColor("#607D8B")),
        "th": ParagraphStyle("th", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white),
        "celda": ParagraphStyle("celda", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=GRIS_OSCURO),
        "centro": ParagraphStyle("centro", parent=base["Normal"], fontName="Helvetica", fontSize=9, alignment=1, textColor=GRIS_OSCURO),
    }


def _seccion(titulo, est):
    tabla = Table([[Paragraph(escape(titulo), est["seccion"])]], colWidths=[ANCHO_UTIL])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL),
                ("LINEBELOW", (0, 0), (-1, -1), 2, ROJO),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tabla


def _tabla_datos(filas, est):
    datos = [[Paragraph(escape(k), est["label"]), Paragraph(_txt(v), est["normal"])] for k, v in filas]
    tabla = Table(datos, colWidths=[4.5 * cm, ANCHO_UTIL - 4.5 * cm])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), GRIS_CLARO),
                ("GRID", (0, 0), (-1, -1), 0.5, GRIS_LINEA),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _encabezado_pie(canvas, doc):
    """Dibuja el header rojo y el pie de página en cada hoja."""
    ancho, alto = letter
    canvas.saveState()

    canvas.setFillColor(ROJO)
    canvas.rect(0, alto - 2.3 * cm, ancho, 2.3 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(2 * cm, alto - 1.35 * cm, EMPRESA.upper())
    canvas.setFont("Helvetica-Oblique", 9)
    canvas.drawString(2 * cm, alto - 1.9 * cm, ESLOGAN)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawRightString(ancho - 2 * cm, alto - 1.35 * cm, "ORDEN DE SERVICIO")

    canvas.setStrokeColor(AZUL)
    canvas.setLineWidth(1)
    canvas.line(2 * cm, 1.6 * cm, ancho - 2 * cm, 1.6 * cm)
    canvas.setFillColor(GRIS_OSCURO)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(2 * cm, 1.1 * cm, f"{EMPRESA} · {ESLOGAN}")
    canvas.drawRightString(ancho - 2 * cm, 1.1 * cm, f"Página {doc.page}")

    canvas.restoreState()


def _imagen_escalada(contenido, max_ancho=8 * cm, max_alto=6 * cm):
    """Crea un Image de ReportLab escalado, o None si el archivo no es una imagen válida."""
    try:
        ancho, alto = ImageReader(BytesIO(contenido)).getSize()
        escala = min(max_ancho / ancho, max_alto / alto, 1.0 if ancho < 1000 else max_ancho / ancho)
        return Image(BytesIO(contenido), width=ancho * escala, height=alto * escala)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def generar_pdf_reporte(reporte, cliente, historial=None, evidencias=None):
    """Genera el PDF de una orden de servicio y devuelve los bytes.

    reporte    : dict de reportes.obtener_reporte()
    cliente    : dict de clientes.obtener_cliente()
    historial  : lista de reportes.historial_reporte()
    evidencias : lista de reportes.listar_evidencias(con_datos=True)
    """
    historial = historial or []
    evidencias = evidencias or []
    cliente = cliente or {}
    est = _estilos()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=3.2 * cm,
        bottomMargin=2.2 * cm,
        title=f"Orden de servicio {reporte['folio']}",
        author=EMPRESA,
    )

    historia = []

    # --- Título y estado ---
    color_estado = ESTADO_COLORES.get(reporte["estado"], "#607D8B")
    historia.append(Paragraph(f"Folio: {_txt(reporte['folio'])}", est["titulo"]))
    barra = Table(
        [
            [
                Paragraph(f"<b>Estado:</b> {_txt(reporte['estado'])}", est["th"]),
                Paragraph(f"<b>Prioridad:</b> {_txt(reporte['prioridad'])}", est["normal"]),
                Paragraph(f"<b>Fecha:</b> {_fecha(reporte['creado_en'])}", est["normal"]),
            ]
        ],
        colWidths=[5.5 * cm, 4.5 * cm, ANCHO_UTIL - 10 * cm],
    )
    barra.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(color_estado)),
                ("BACKGROUND", (1, 0), (-1, 0), GRIS_CLARO),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    historia.extend([Spacer(1, 6), barra, Spacer(1, 12)])

    # --- Cliente ---
    historia.append(_seccion("DATOS DEL CLIENTE", est))
    historia.append(
        _tabla_datos(
            [
                ("Nombre", cliente.get("nombre") or reporte.get("cliente_nombre")),
                ("Empresa", cliente.get("empresa") or reporte.get("cliente_empresa")),
                ("Teléfono", cliente.get("telefono")),
                ("Correo", cliente.get("email")),
                ("RFC", cliente.get("rfc")),
                ("Dirección", cliente.get("direccion")),
            ],
            est,
        )
    )
    historia.append(Spacer(1, 10))

    # --- Equipo ---
    historia.append(_seccion("DATOS DEL EQUIPO Y SERVICIO", est))
    historia.append(
        _tabla_datos(
            [
                ("Tipo de servicio", reporte.get("tipo_servicio")),
                ("Equipo / Herramienta", reporte.get("equipo")),
                ("Marca", reporte.get("marca")),
                ("Modelo", reporte.get("modelo")),
                ("Número de serie", reporte.get("numero_serie")),
                ("Registrado por", reporte.get("creado_por_nombre")),
                ("Técnico asignado", reporte.get("tecnico_nombre") or "Sin asignar"),
            ],
            est,
        )
    )
    historia.append(Spacer(1, 10))

    # --- Problema y diagnóstico ---
    historia.append(_seccion("DESCRIPCIÓN DEL PROBLEMA", est))
    historia.append(Spacer(1, 4))
    historia.append(Paragraph(_txt(reporte.get("descripcion_problema")), est["normal"]))
    historia.append(Spacer(1, 10))

    historia.append(_seccion("DIAGNÓSTICO / TRABAJO REALIZADO", est))
    historia.append(Spacer(1, 4))
    historia.append(Paragraph(_txt(reporte.get("diagnostico")), est["normal"]))
    historia.append(Spacer(1, 10))

    # --- Historial ---
    if historial:
        historia.append(_seccion("HISTORIAL DE ESTADOS", est))
        filas = [
            [Paragraph(t, est["th"]) for t in ("Fecha", "Usuario", "De", "A", "Comentario")]
        ]
        for h in historial:
            filas.append(
                [
                    Paragraph(_fecha(h.get("creado_en")), est["celda"]),
                    Paragraph(_txt(h.get("usuario_nombre")), est["celda"]),
                    Paragraph(_txt(h.get("estado_anterior")), est["celda"]),
                    Paragraph(_txt(h.get("estado_nuevo")), est["celda"]),
                    Paragraph(_txt(h.get("comentario")), est["celda"]),
                ]
            )
        tabla = Table(
            filas,
            colWidths=[3.0 * cm, 3.4 * cm, 2.9 * cm, 2.9 * cm, ANCHO_UTIL - 12.2 * cm],
            repeatRows=1,
        )
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GRIS_OSCURO),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRIS_LINEA),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        historia.append(tabla)
        historia.append(Spacer(1, 10))

    # --- Evidencias ---
    if evidencias:
        historia.append(_seccion("EVIDENCIAS", est))
        historia.append(Spacer(1, 6))
        mostradas = 0
        otros = []
        for ev in evidencias:
            es_imagen = (ev.get("tipo_mime") or "").startswith("image/")
            imagen = _imagen_escalada(ev["archivo"]) if es_imagen and mostradas < MAX_IMAGENES else None
            if imagen is not None:
                mostradas += 1
                pie = Paragraph(
                    f"<b>{_txt(ev.get('nombre_archivo'))}</b> — {_txt(ev.get('descripcion'))}",
                    est["pequeno"],
                )
                historia.append(KeepTogether([imagen, pie, Spacer(1, 8)]))
            else:
                otros.append(ev.get("nombre_archivo"))
        if otros:
            historia.append(
                Paragraph("Otros archivos adjuntos: " + ", ".join(_txt(o) for o in otros), est["normal"])
            )
        historia.append(Spacer(1, 10))

    # --- Firmas ---
    firmas = Table(
        [
            ["", ""],
            [Paragraph("Firma del técnico", est["centro"]), Paragraph("Firma de conformidad del cliente", est["centro"])],
        ],
        colWidths=[ANCHO_UTIL / 2, ANCHO_UTIL / 2],
        rowHeights=[1.8 * cm, None],
    )
    firmas.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 1), (0, 1), 0.8, GRIS_OSCURO),
                ("LINEABOVE", (1, 1), (1, 1), 0.8, GRIS_OSCURO),
                ("LEFTPADDING", (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ]
        )
    )
    historia.append(KeepTogether([Spacer(1, 12), firmas]))
    historia.append(Spacer(1, 10))
    historia.append(
        Paragraph(
            f"Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} por el sistema {EMPRESA}.",
            est["pequeno"],
        )
    )

    doc.build(historia, onFirstPage=_encabezado_pie, onLaterPages=_encabezado_pie)
    return buffer.getvalue()
