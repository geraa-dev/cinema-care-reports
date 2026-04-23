from flask import Flask, render_template, request, jsonify, send_file
import os, json, base64, io
from datetime import datetime
import uuid

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── BASE DE DATOS DE ERRORES ──────────────────────────────────────────────────
ERROR_DB = {
    "E001": {
        "nombre": "Imagen Distorsionada / Artefactos Visuales",
        "categoria": "Proyección",
        "pasos": [
            {
                "id": 1,
                "titulo": "Verificar cable de señal",
                "descripcion": "Desconecta y reconecta el cable HDMI/DisplayPort del proyector. Inspecciona que no tenga dobleces ni daños físicos visibles. Asegúrate de que esté completamente insertado en ambos extremos.",
                "herramienta": "Cable HDMI/DP de repuesto (si hay disponible)"
            },
            {
                "id": 2,
                "titulo": "Reiniciar servidor de medios (TMS)",
                "descripcion": "Ve al rack de equipos. Apaga el servidor TMS con el botón de encendido. Espera 30 segundos completos. Enciéndelo de nuevo y espera 2 minutos a que cargue el sistema operativo.",
                "herramienta": "Acceso al rack de equipos"
            },
            {
                "id": 3,
                "titulo": "Verificar configuración de resolución",
                "descripcion": "Desde el menú del proyector (botón MENU en el panel), navega a Configuración > Señal de entrada. Confirma que la resolución coincide con la del servidor (usualmente 2048x1080 para 2K o 4096x2160 para 4K).",
                "herramienta": "Control remoto del proyector"
            },
            {
                "id": 4,
                "titulo": "Cambiar puerto de entrada en proyector",
                "descripcion": "Desde el panel frontal del proyector, selecciona una entrada diferente (ej: HDMI 2 o SDI). Verifica si la imagen mejora. Si el proyector tiene dos puertos, prueba el alternativo.",
                "herramienta": "Panel frontal del proyector"
            },
            {
                "id": 5,
                "titulo": "Diagnóstico de tarjeta gráfica",
                "descripcion": "En el servidor de medios, accede al administrador de dispositivos (clic derecho en Mi PC > Administrar). Busca 'Adaptadores de pantalla'. Si hay un símbolo de advertencia amarillo, el driver está corrupto. Anota el modelo de la tarjeta.",
                "herramienta": "Teclado y mouse en servidor TMS"
            }
        ]
    },
    "E002": {
        "nombre": "Sin Audio / Audio Intermitente",
        "categoria": "Audio",
        "pasos": [
            {
                "id": 1,
                "titulo": "Verificar que el procesador de audio este prendido",
                "descripcion": "Localiza el procesador de audio (en la parte superior del rack de audio, marca QSC o Dolby CP 650/750/850/950 o JBL CPI2000). Verifica que el procesador este encendido ya sea emitiendo luz en el panel o mediante el ventilador.",
                "herramienta": "Acceso al procesador de audio"
            },
            {
                "id": 2,
                "titulo": "Revisa que el canal activado sea DIGITAL y el fader no este en 0 o MUTE(normalmente el canal 1)",
                "descripcion": "inspecciona los botones y el canal 1 debe estar marcado como activado en los DOLBY / En los JBL debe estar marcado el icono de la pelicula, igualmente asegurate de que no este en MUTE el procesador de audio ",
                "herramienta": "Cables XLR de repuesto (opcional)"
            },
            {
                "id": 3,
                "titulo": "Verifica que los amplificadores esten prendidos",
                "descripcion": "Verifica todos y cada uno de los amplificadores que esten encendidos, de no estarlo, revisa las conexiones fisicas de atras",
                "herramienta": "Procesador de audio"
            },
            {
                "id": 4,
                "titulo": "Reinicia el procesador de Audio",
                "descripcion": "Presiona el boton de POWER para apagarlo (CP750 se desconecta directo de el cable de poder) una vez apagado, desconecta el procesador del cable de alimentacion y espera 30 segundos, una vez pasado ese tiempo vuleve a conectar y ejecuta una prueba",
                "herramienta": "Software TMS (pantalla de administración)"
            }
        ]
    },
    "E003": {
        "nombre": "Proyector No Enciende",
        "categoria": "Proyección",
        "pasos": [
            {
                "id": 1,
                "titulo": "Verificar alimentación eléctrica",
                "descripcion": "Revisa que el breaker del proyector esté en posición ON en el tablero eléctrico de la cabina. Verifica también que el cable de poder del proyector esté bien conectado a la PDU (regleta de poder del rack).",
                "herramienta": "Tablero eléctrico de cabina"
            },
            {
                "id": 2,
                "titulo": "Revisar luz indicadora de estado",
                "descripcion": "Observa el LED de estado en el panel del proyector: VERDE = OK, AMARILLO = precaución, ROJO = error crítico, PARPADEANDO = modo de espera. Fotografía el color del LED para el reporte.",
                "herramienta": "Inspección visual directa"
            },
            {
                "id": 3,
                "titulo": "Forzar encendido desde panel",
                "descripcion": "Presiona y mantén el botón POWER en el panel frontal por 5 segundos. Si no responde, verifica si el sistema tiene doble interruptor (algunos proyectores Barco/Christie tienen interruptor de llave).",
                "herramienta": "Panel frontal del proyector"
            },
            {
                "id": 4,
                "titulo": "Revisar temperatura del láser/xenón",
                "descripcion": "Accede al menú de diagnóstico del proyector (MENU > Diagnóstico > Temperatura). Si la temperatura de la fuente de luz supera 85°C, el proyector se apaga por protección térmica. Verifica que los ventiladores estén funcionando.",
                "herramienta": "Menú de diagnóstico del proyector"
            }
        ]
    },
    "E004": {
        "nombre": "Pantalla Negra / Sin Señal",
        "categoria": "Proyección",
        "pasos": [
            {
                "id": 1,
                "titulo": "Verificar que el obturador esté abierto",
                "descripcion": "El proyector puede estar proyectando pero con el obturador (douser) cerrado. Busca el botón 'DOUSER' o 'SHUTTER' en el panel del proyector o en el software de control. Presiónalo para abrir.",
                "herramienta": "Panel frontal o software de control"
            },
            {
                "id": 2,
                "titulo": "Confirmar reproducción en TMS",
                "descripcion": "Ve al servidor TMS y verifica que el contenido esté en estado 'PLAYING' (reproduciendo). Si está en 'PAUSED' o 'STOPPED', inicia la reproducción manualmente desde la interfaz del TMS.",
                "herramienta": "Interfaz TMS"
            },
            {
                "id": 3,
                "titulo": "Revisar link de automatización",
                "descripcion": "Algunos sistemas automatizan el encendido/apagado del douser con la automatización de sala. Verifica en el software de automatización (GDC, Dolby ShowVault) que la secuencia de encendido completó todos sus pasos.",
                "herramienta": "Software de automatización"
            },
            {
                "id": 4,
                "titulo": "Probar entrada de señal alternativa",
                "descripcion": "Conecta un laptop o reproductor de prueba al proyector usando un adaptador HDMI. Si aparece imagen, el problema es del servidor TMS o el cable. Si sigue sin imagen, es del proyector o su configuración.",
                "herramienta": "Laptop + cable HDMI"
            }
        ]
    },
    "E005": {
        "nombre": "Error de Certificado KDM",
        "categoria": "Software / Seguridad",
        "pasos": [
            {
                "id": 1,
                "titulo": "Verificar fecha y hora del servidor",
                "descripcion": "El KDM (llave de descifrado) es válido solo en un rango de fechas específico. Ve al servidor TMS y verifica la fecha y hora del sistema. Si hay discrepancia de más de 5 minutos, el KDM será rechazado.",
                "herramienta": "Configuración del servidor TMS"
            },
            {
                "id": 2,
                "titulo": "Confirmar vigencia del KDM",
                "descripcion": "En el software TMS, selecciona el contenido y revisa las propiedades del KDM. Verifica: Fecha de inicio (no puede usarse antes), Fecha de fin (venció), y Número de sala (el KDM es exclusivo para una sala específica).",
                "herramienta": "Software TMS > Gestión de KDMs"
            },
            {
                "id": 3,
                "titulo": "Re-importar KDM desde archivo",
                "descripcion": "Si tienes el archivo KDM (.kdm.xml) en tu correo o en un USB, impórtalo nuevamente desde TMS > Importar KDM. Asegúrate de importar el archivo correcto para esta sala y esta película.",
                "herramienta": "Archivo KDM (correo o USB)"
            },
            {
                "id": 4,
                "titulo": "Verificar fingerprint del servidor",
                "descripcion": "El KDM fue generado para el certificado único de este servidor. En TMS > Información del sistema, copia el 'Certificate Fingerprint'. Compáralo con el que aparece en el correo del KDM. Deben coincidir.",
                "herramienta": "TMS > Información del sistema"
            }
        ]
    },
    "E0455": {
        "nombre": "Error de Certificado KDMMMM",
        "categoria": "Software / Seguridad",
        "pasos": [
            {
                "id": 1,
                "titulo": "Verificar fecha y hora del servidor",
                "descripcion": "El KDM (llave de descifrado) es válido solo en un rango de fechas específico. Ve al servidor TMS y verifica la fecha y hora del sistema. Si hay discrepancia de más de 5 minutos, el KDM será rechazado.",
                "herramienta": "Configuración del servidor TMS"
            },
            {
                "id": 2,
                "titulo": "Confirmar vigencia del KDM",
                "descripcion": "En el software TMS, selecciona el contenido y revisa las propiedades del KDM. Verifica: Fecha de inicio (no puede usarse antes), Fecha de fin (venció), y Número de sala (el KDM es exclusivo para una sala específica).",
                "herramienta": "Software TMS > Gestión de KDMs"
            },
            {
                "id": 3,
                "titulo": "Re-importar KDM desde archivo",
                "descripcion": "Si tienes el archivo KDM (.kdm.xml) en tu correo o en un USB, impórtalo nuevamente desde TMS > Importar KDM. Asegúrate de importar el archivo correcto para esta sala y esta película.",
                "herramienta": "Archivo KDM (correo o USB)"
            },
            {
                "id": 4,
                "titulo": "Verificar fingerprint del servidor",
                "descripcion": "El KDM fue generado para el certificado único de este servidor. En TMS > Información del sistema, copia el 'Certificate Fingerprint'. Compáralo con el que aparece en el correo del KDM. Deben coincidir.",
                "herramienta": "TMS > Información del sistema"
            }
        ]
    }
}

# ─── BASE DE DATOS EN MEMORIA (Reemplazar con DB real en producción) ───────────
incidents_db = []

# ─── RUTAS ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Lista todos los errores disponibles para el buscador."""
    errors = [
        {"codigo": code, "nombre": data["nombre"], "categoria": data["categoria"]}
        for code, data in ERROR_DB.items()
    ]
    return jsonify(errors)

@app.route('/api/error/<code>', methods=['GET'])
def get_error(code):
    """Devuelve los pasos de un error específico."""
    error = ERROR_DB.get(code.upper())
    if not error:
        return jsonify({"error": "Código no encontrado"}), 404
    return jsonify({"codigo": code.upper(), **error})

@app.route('/api/resolve', methods=['POST'])
def resolve_incident():
    """Guarda un incidente resuelto en la base de datos."""
    data = request.json
    incident_id = data.get('incident_id')
    photo_url = None
    photos = []

    # Procesar foto si viene en base64
    if data.get('photo_b64'):
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        img_data = data['photo_b64'].split(',')[-1]
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(img_data))
        photo_url = f"/static/uploads/{filename}"
        
        # ✅ Guardamos la foto con informacion del paso correspondiente
        photos.append({
            "url": photo_url,
            "paso": data.get('paso_resolucion'),
            "titulo_paso": data.get('titulo_paso'),
            "fecha": datetime.now().strftime('%d/%m/%Y %H:%M')
        })

    # ✅ Si el incidente ya existe, actualizamos agregando la nueva foto
    existing = next((i for i in incidents_db if i['id'] == incident_id), None)
    if existing:
        # ✅ ✅ CORRECCION CRITICA: SIEMPRE inicializamos el array de fotos aunque no venga foto nueva
        if 'photos' not in existing:
            existing['photos'] = []
            # Migramos foto antigua si existia
            if existing.get('photo_url'):
                existing['photos'].append({
                    "url": existing['photo_url'],
                    "paso": existing['paso_resolucion'],
                    "titulo_paso": existing['titulo_paso'],
                    "fecha": existing['fecha']
                })
        # ✅ Agregamos la nueva foto SIEMPRE que exista
        if photo_url:
            existing['photos'].extend(photos)
            
        existing['paso_resolucion'] = data.get('paso_resolucion')
        existing['titulo_paso'] = data.get('titulo_paso')
        existing['notas'] = data.get('notas', existing.get('notas', ''))
        existing['fecha'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        return jsonify({"success": True, "incident_id": incident_id, "photos_count": len(existing['photos'])})

    # ✅ Incidente nuevo
    incident = {
        "id": str(uuid.uuid4())[:8].upper(),
        "error_codigo": data.get('error_codigo'),
        "error_nombre": data.get('error_nombre'),
        "sala": data.get('sala', 'Sin especificar'),
        "paso_resolucion": data.get('paso_resolucion'),
        "titulo_paso": data.get('titulo_paso'),
        "tecnico": data.get('tecnico', 'Anónimo'),
        "fecha": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "photo_url": photo_url,
        "photos": photos,
        "notas": data.get('notas', '')
    }
    incidents_db.append(incident)
    return jsonify({"success": True, "incident_id": incident["id"], "photos_count": len(photos)})

@app.route('/api/escalate', methods=['POST'])
def escalate_incident():
    """Registra un escalamiento a técnico senior."""
    data = request.json
    incident_id = data.get('incident_id')
    photos = []
    photo_url = None

    # ✅ SI EXISTE EL INCIDENTE: ACTUALIZAMOS EL MISMO, NO CREAMOS UNO NUEVO
    existing = next((i for i in incidents_db if i['id'] == incident_id), None)
    if existing:
        # Copiamos todas las fotografias ya subidas
        if existing.get('photos'):
            photos = existing['photos'].copy()
        elif existing.get('photo_url'):
            photos.append({
                "url": existing['photo_url'],
                "paso": existing['paso_resolucion'],
                "titulo_paso": existing['titulo_paso'],
                "fecha": existing['fecha']
            })

        # ✅ Agregamos la nueva foto del momento del escalado si viene
        if data.get('photo_b64'):
            filename = f"{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            img_data = data['photo_b64'].split(',')[-1]
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(img_data))
            photo_url = f"/static/uploads/{filename}"
            photos.append({
                "url": photo_url,
                "paso": "FINAL",
                "titulo_paso": "Momento de escalamiento de incidente",
                "fecha": datetime.now().strftime('%d/%m/%Y %H:%M')
            })

        # ✅ ACTUALIZAMOS EL INCIDENTE EXISTENTE
        existing['photos'] = photos
        existing['paso_resolucion'] = "ESCALADO - Todos los pasos fallaron"
        existing['titulo_paso'] = "Solicitud de Técnico Senior"
        existing['escalado'] = True
        existing['notas'] = f"ESCALADO: {data.get('notas', '')}"
        existing['fecha'] = datetime.now().strftime('%d/%m/%Y %H:%M')

        # En producción: enviar email, SMS, webhook a técnico senior
        return jsonify({"success": True, "incident_id": incident_id, "photos_count": len(photos), "message": "Técnico senior notificado"})

    # ✅ Solo si no existe el incidente, creamos uno nuevo
    incident = {
        "id": str(uuid.uuid4())[:8].upper(),
        "error_codigo": data.get('error_codigo'),
        "error_nombre": data.get('error_nombre'),
        "sala": data.get('sala', 'Sin especificar'),
        "paso_resolucion": "ESCALADO - Todos los pasos fallaron",
        "titulo_paso": "Solicitud de Técnico Senior",
        "tecnico": data.get('tecnico', 'Anónimo'),
        "fecha": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "photo_url": photo_url,
        "photos": photos,
        "notas": f"ESCALADO: {data.get('notas', '')}",
        "escalado": True
    }
    incidents_db.append(incident)
    
    # En producción: enviar email, SMS, webhook a técnico senior
    return jsonify({"success": True, "incident_id": incident["id"], "photos_count": len(photos), "message": "Técnico senior notificado"})

@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    return jsonify(incidents_db[::-1])  # Más recientes primero

@app.route('/admin')
def admin():
    return render_template('admin.html', incidents=incidents_db[::-1])

# ─── PDF: REPORTE INDIVIDUAL DE UN INCIDENTE ──────────────────────────────────
@app.route('/api/report/incident/<incident_id>')
def report_incident(incident_id):
    """Genera PDF de un incidente específico con toda su evidencia fotográfica."""
    inc = next((i for i in incidents_db if i['id'] == incident_id), None)
    if not inc:
        return "Incidente no encontrado", 404
    pdf_buffer = generate_incident_pdf(inc)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"CinemaCare_Incidente_{incident_id}_{inc['sala'].replace(' ','_')}.pdf"
    )

# ─── PDF: REPORTE GLOBAL DE TODOS LOS INCIDENTES ──────────────────────────────
@app.route('/api/report/all')
def report_all():
    """Genera PDF con el reporte completo de todos los incidentes."""
    if not incidents_db:
        return "No hay incidentes registrados", 404
    pdf_buffer = generate_all_incidents_pdf(incidents_db[::-1])
    fecha = datetime.now().strftime('%Y%m%d_%H%M')
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"CinemaCare_Reporte_Completo_{fecha}.pdf"
    )

# ─── GENERADOR DE PDF INDIVIDUAL ──────────────────────────────────────────────
def generate_incident_pdf(inc):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    # ── Paleta de colores ──
    C_BG_DARK    = colors.HexColor('#0a0c10')
    C_ELECTRIC   = colors.HexColor('#00d4ff')
    C_ELECTRIC_D = colors.HexColor('#0077aa')
    C_SUCCESS    = colors.HexColor('#00c87a')
    C_DANGER     = colors.HexColor('#ff3860')
    C_TEXT       = colors.HexColor('#1a1a2e')
    C_MUTED      = colors.HexColor('#5a6a80')
    C_PANEL      = colors.HexColor('#f0f4f8')
    C_BORDER     = colors.HexColor('#d0dce8')
    C_WHITE      = colors.white

    # ── Estilos ──
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('CTitle', fontName='Helvetica-Bold', fontSize=22,
                                  textColor=C_BG_DARK, spaceAfter=4, leading=26)
    style_subtitle = ParagraphStyle('CSub', fontName='Helvetica', fontSize=10,
                                     textColor=C_MUTED, spaceAfter=2)
    style_section = ParagraphStyle('CSection', fontName='Helvetica-Bold', fontSize=11,
                                    textColor=C_ELECTRIC_D, spaceBefore=14, spaceAfter=6,
                                    borderPad=4)
    style_label = ParagraphStyle('CLabel', fontName='Helvetica-Bold', fontSize=8,
                                  textColor=C_MUTED, spaceAfter=1, leading=10)
    style_value = ParagraphStyle('CValue', fontName='Helvetica', fontSize=10,
                                  textColor=C_TEXT, spaceAfter=2, leading=14)
    style_body = ParagraphStyle('CBody', fontName='Helvetica', fontSize=9,
                                 textColor=C_TEXT, leading=14, spaceAfter=4)
    style_note = ParagraphStyle('CNote', fontName='Helvetica-Oblique', fontSize=9,
                                 textColor=C_MUTED, leading=13)
    style_step_title = ParagraphStyle('CStepT', fontName='Helvetica-Bold', fontSize=10,
                                       textColor=C_BG_DARK, leading=14)
    style_footer = ParagraphStyle('CFooter', fontName='Helvetica', fontSize=7,
                                   textColor=C_MUTED, alignment=TA_CENTER)

    story = []
    is_escalated = inc.get('escalado', False)
    status_color = C_DANGER if is_escalated else C_SUCCESS
    status_text  = 'ESCALADO — TÉCNICO SENIOR REQUERIDO' if is_escalated else 'RESUELTO POR STAFF'

    # ══════════════════════════════════════════════════════════════════
    # ENCABEZADO
    # ══════════════════════════════════════════════════════════════════
    header_data = [[
        Paragraph('<b>🎬 CINEMACARE PRO</b>', ParagraphStyle('H', fontName='Helvetica-Bold',
                  fontSize=18, textColor=C_ELECTRIC, leading=22)),
        Paragraph(f'<b>REPORTE DE INCIDENTE</b><br/><font size="8" color="#5a6a80">ID: #{inc["id"]}</font>',
                  ParagraphStyle('HR', fontName='Helvetica-Bold', fontSize=12,
                                 textColor=C_BG_DARK, alignment=TA_RIGHT, leading=18))
    ]]
    header_table = Table(header_data, colWidths=['60%', '40%'])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_DARK),
        ('TOPPADDING', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (0,-1), 16),
        ('RIGHTPADDING', (-1,0), (-1,-1), 16),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # BADGE DE ESTADO
    badge_data = [[Paragraph(f'<b>  ● {status_text}  </b>',
                             ParagraphStyle('Badge', fontName='Helvetica-Bold', fontSize=10,
                                           textColor=C_WHITE, alignment=TA_CENTER))]]
    badge_table = Table(badge_data, colWidths=['100%'])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), status_color),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 16))

    # ══════════════════════════════════════════════════════════════════
    # DATOS DEL INCIDENTE — tabla de 4 celdas
    # ══════════════════════════════════════════════════════════════════
    story.append(Paragraph('INFORMACIÓN DEL INCIDENTE', style_section))

    def info_cell(label, value):
        return [Paragraph(label, style_label), Paragraph(str(value), style_value)]

    paso_texto = (f"Paso {inc['paso_resolucion']} — {inc['titulo_paso']}"
                  if not is_escalated else "Todos los pasos agotados (escalado)")

    info_data = [
        [info_cell('CÓDIGO DE ERROR', inc['error_codigo']),
         info_cell('CATEGORÍA / FALLA', inc['error_nombre'])],
        [info_cell('SALA / AUDITORIUM', inc['sala']),
         info_cell('TÉCNICO RESPONSABLE', inc['tecnico'])],
        [info_cell('FECHA Y HORA', inc['fecha']),
         info_cell('PASO DE RESOLUCIÓN', paso_texto)],
    ]

    flat_data = []
    for row in info_data:
        flat_row = []
        for cell in row:
            flat_row.append(cell[0])  # label
            flat_row.append(cell[1])  # value
        flat_data.append(flat_row)

    info_table = Table(flat_data, colWidths=['16%', '34%', '16%', '34%'])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_PANEL),
        ('BACKGROUND', (0,0), (0,-1), C_PANEL),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    # ══════════════════════════════════════════════════════════════════
    # NOTAS DEL TÉCNICO
    # ══════════════════════════════════════════════════════════════════
    if inc.get('notas'):
        story.append(Paragraph('NOTAS DEL TÉCNICO', style_section))
        notes_data = [[Paragraph(inc['notas'], style_note)]]
        notes_table = Table(notes_data, colWidths=['100%'])
        notes_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fff8e8')),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#f0c040')),
            ('ROUNDEDCORNERS', [4]),
        ]))
        story.append(notes_table)
        story.append(Spacer(1, 16))

    # ══════════════════════════════════════════════════════════════════
    # EVIDENCIA FOTOGRÁFICA
    # ══════════════════════════════════════════════════════════════════
    story.append(Paragraph('EVIDENCIA FOTOGRÁFICA', style_section))

    # ✅ MULTIPLES FOTOS: Recorremos TODAS las fotografias adjuntas por paso
    all_photos = []
    
    # Cargamos fotos del nuevo formato
    if inc.get('photos') and len(inc['photos']) > 0:
        all_photos = inc['photos']
    # Compatibilidad hacia atras con incidentes antiguos de 1 sola foto
    elif inc.get('photo_url'):
        all_photos.append({
            "url": inc['photo_url'],
            "paso": inc['paso_resolucion'],
            "titulo_paso": inc['titulo_paso'],
            "fecha": inc['fecha']
        })

    if len(all_photos) > 0:
        for idx, photo in enumerate(all_photos, 1):
            try:
                relative_parts = photo['url'].strip('/').split('/')
                photo_path = os.path.join(os.getcwd(), *relative_parts)
                
                if os.path.exists(photo_path):
                    img = RLImage(photo_path, width=14*cm, height=10*cm, kind='proportional')
                    img_data = [[img]]
                    img_table = Table(img_data, colWidths=['100%'])
                    img_table.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('TOPPADDING', (0,0), (-1,-1), 10),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                        ('BOX', (0,0), (-1,-1), 1.5, C_ELECTRIC_D),
                        ('BACKGROUND', (0,0), (-1,-1), C_PANEL),
                        ('ROUNDEDCORNERS', [4]),
                    ]))
                    story.append(img_table)
                    story.append(Spacer(1, 4))
                    story.append(Paragraph(
                        f'📷 Foto {idx} | Paso {photo["paso"]} — {photo["titulo_paso"]} — {photo["fecha"]}',
                        ParagraphStyle('Caption', fontName='Helvetica-Oblique', fontSize=8,
                                       textColor=C_MUTED, alignment=TA_CENTER)
                    ))
                    story.append(Spacer(1, 12))
            except Exception as e:
                story.append(Paragraph(f'[Error cargando imagen: {e}]', style_note))
    else:
        no_photo_data = [[Paragraph('📷  Sin fotografía de evidencia adjunta en este incidente.',
                                    ParagraphStyle('NP', fontName='Helvetica-Oblique', fontSize=9,
                                                   textColor=C_MUTED, alignment=TA_CENTER))]]
        np_table = Table(no_photo_data, colWidths=['100%'])
        np_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), C_PANEL),
            ('TOPPADDING', (0,0), (-1,-1), 20),
            ('BOTTOMPADDING', (0,0), (-1,-1), 20),
            ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
            ('ROUNDEDCORNERS', [4]),
        ]))
        story.append(np_table)

    story.append(Spacer(1, 20))

    # ── PIE DE PÁGINA ──
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f'CinemaCare Pro · Reporte generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} · '
        f'Incidente #{inc["id"]} · Documento confidencial de mantenimiento',
        style_footer
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ─── GENERADOR DE PDF COMPLETO ────────────────────────────────────────────────
def generate_all_incidents_pdf(incidents):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    C_BG_DARK    = colors.HexColor('#0a0c10')
    C_ELECTRIC   = colors.HexColor('#00d4ff')
    C_ELECTRIC_D = colors.HexColor('#0077aa')
    C_SUCCESS    = colors.HexColor('#00c87a')
    C_DANGER     = colors.HexColor('#ff3860')
    C_TEXT       = colors.HexColor('#1a1a2e')
    C_MUTED      = colors.HexColor('#5a6a80')
    C_PANEL      = colors.HexColor('#f0f4f8')
    C_BORDER     = colors.HexColor('#d0dce8')
    C_WHITE      = colors.white
    C_ROW_ALT    = colors.HexColor('#f7fafd')

    styles = getSampleStyleSheet()
    style_section = ParagraphStyle('Sec', fontName='Helvetica-Bold', fontSize=11,
                                    textColor=C_ELECTRIC_D, spaceBefore=10, spaceAfter=6)
    style_footer  = ParagraphStyle('Ft', fontName='Helvetica', fontSize=7,
                                    textColor=C_MUTED, alignment=TA_CENTER)
    style_note    = ParagraphStyle('Nt', fontName='Helvetica-Oblique', fontSize=8,
                                    textColor=C_MUTED)
    style_label   = ParagraphStyle('Lb', fontName='Helvetica-Bold', fontSize=7,
                                    textColor=C_MUTED)
    style_val     = ParagraphStyle('Vl', fontName='Helvetica', fontSize=9, textColor=C_TEXT)
    style_caption = ParagraphStyle('Cap', fontName='Helvetica-Oblique', fontSize=7,
                                    textColor=C_MUTED, alignment=TA_CENTER)

    story = []
    total      = len(incidents)
    escalados  = sum(1 for i in incidents if i.get('escalado'))
    resueltos  = total - escalados
    tasa       = round((resueltos / total * 100)) if total else 0

    # ══ PORTADA ══════════════════════════════════════════════════════
    header_data = [[
        Paragraph('<b>🎬 CINEMACARE PRO</b>',
                  ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=20,
                                 textColor=C_ELECTRIC, leading=24)),
        Paragraph('<b>REPORTE COMPLETO DE INCIDENTES</b><br/>'
                  f'<font size="8" color="#aaaaaa">Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}</font>',
                  ParagraphStyle('HR', fontName='Helvetica-Bold', fontSize=12,
                                 textColor=C_WHITE, alignment=TA_RIGHT, leading=18))
    ]]
    ht = Table(header_data, colWidths=['55%', '45%'])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_DARK),
        ('TOPPADDING', (0,0), (-1,-1), 16),
        ('BOTTOMPADDING', (0,0), (-1,-1), 16),
        ('LEFTPADDING', (0,0), (0,-1), 16),
        ('RIGHTPADDING', (-1,0), (-1,-1), 16),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(ht)
    story.append(Spacer(1, 12))

    # ══ KPIs ═════════════════════════════════════════════════════════
    kpi_data = [[
        [Paragraph('TOTAL', style_label),
         Paragraph(f'<b>{total}</b>', ParagraphStyle('K', fontName='Helvetica-Bold',
                   fontSize=26, textColor=C_ELECTRIC_D, leading=30))],
        [Paragraph('RESUELTOS', style_label),
         Paragraph(f'<b>{resueltos}</b>', ParagraphStyle('K', fontName='Helvetica-Bold',
                   fontSize=26, textColor=C_SUCCESS, leading=30))],
        [Paragraph('ESCALADOS', style_label),
         Paragraph(f'<b>{escalados}</b>', ParagraphStyle('K', fontName='Helvetica-Bold',
                   fontSize=26, textColor=C_DANGER, leading=30))],
        [Paragraph('TASA RESOLUCIÓN', style_label),
         Paragraph(f'<b>{tasa}%</b>', ParagraphStyle('K', fontName='Helvetica-Bold',
                   fontSize=26, textColor=colors.HexColor('#ff9900'), leading=30))],
    ]]
    # Flatten nested lists for ReportLab Table
    kpi_flat = [[
        '\n'.join([str(c) for c in cell]) if isinstance(cell, list) else cell
        for cell in row
    ] for row in kpi_data]

    # Build as separate paragraphs in table
    kpi_cells = []
    for item in kpi_data:
        cell_content = [item[0], item[1]]
        kpi_cells.append(cell_content)

    kpi_table_data = [[
        [Paragraph('TOTAL', style_label),
         Paragraph(f'<b>{total}</b>', ParagraphStyle('KV', fontName='Helvetica-Bold', fontSize=24, textColor=C_ELECTRIC_D))],
        [Paragraph('RESUELTOS', style_label),
         Paragraph(f'<b>{resueltos}</b>', ParagraphStyle('KV2', fontName='Helvetica-Bold', fontSize=24, textColor=C_SUCCESS))],
        [Paragraph('ESCALADOS', style_label),
         Paragraph(f'<b>{escalados}</b>', ParagraphStyle('KV3', fontName='Helvetica-Bold', fontSize=24, textColor=C_DANGER))],
        [Paragraph('TASA', style_label),
         Paragraph(f'<b>{tasa}%</b>', ParagraphStyle('KV4', fontName='Helvetica-Bold', fontSize=24, textColor=colors.HexColor('#ff9900')))],
    ]]

    kpi_t = Table(kpi_table_data[0], colWidths=['25%', '25%', '25%', '25%'])
    kpi_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_PANEL),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 20))

    # ══ TABLA RESUMEN DE TODOS LOS INCIDENTES ════════════════════════
    story.append(Paragraph('REGISTRO COMPLETO DE INCIDENTES', style_section))

    table_header = ['ID', 'ESTADO', 'ERROR', 'SALA', 'TÉCNICO', 'PASO', 'FECHA']
    rows = [table_header]
    for inc in incidents:
        is_esc = inc.get('escalado', False)
        status_p = Paragraph(
            f'<b>{"ESCALADO" if is_esc else "RESUELTO"}</b>',
            ParagraphStyle('St', fontName='Helvetica-Bold', fontSize=7,
                           textColor=C_DANGER if is_esc else C_SUCCESS)
        )
        paso_txt = (f'Paso {inc["paso_resolucion"]}' if not is_esc else 'Escalado')
        rows.append([
            Paragraph(f'<b>#{inc["id"]}</b>', ParagraphStyle('ID', fontName='Helvetica-Bold',
                      fontSize=7, textColor=C_ELECTRIC_D)),
            status_p,
            Paragraph(f'{inc["error_codigo"]}\n{inc["error_nombre"][:30]}',
                      ParagraphStyle('En', fontName='Helvetica', fontSize=7, textColor=C_TEXT, leading=10)),
            Paragraph(inc['sala'], ParagraphStyle('Sa', fontName='Helvetica', fontSize=8, textColor=C_TEXT)),
            Paragraph(inc['tecnico'], ParagraphStyle('Te', fontName='Helvetica', fontSize=8, textColor=C_TEXT)),
            Paragraph(paso_txt, ParagraphStyle('Pa', fontName='Helvetica', fontSize=8, textColor=C_TEXT)),
            Paragraph(inc['fecha'], ParagraphStyle('Fe', fontName='Helvetica', fontSize=7, textColor=C_MUTED)),
        ])

    col_w = [1.4*cm, 2*cm, 4.5*cm, 2.2*cm, 2.5*cm, 1.8*cm, 2.3*cm]
    sum_table = Table(rows, colWidths=col_w, repeatRows=1)

    ts = [
        ('BACKGROUND', (0,0), (-1,0), C_BG_DARK),
        ('TEXTCOLOR', (0,0), (-1,0), C_WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.3, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            ts.append(('BACKGROUND', (0,i), (-1,i), C_ROW_ALT))
    sum_table.setStyle(TableStyle(ts))
    story.append(sum_table)
    story.append(PageBreak())

    # ══ DETALLE POR INCIDENTE CON FOTOS ══════════════════════════════
    story.append(Paragraph('DETALLE COMPLETO POR INCIDENTE', style_section))
    story.append(Spacer(1, 6))

    for idx, inc in enumerate(incidents):
        is_esc = inc.get('escalado', False)
        status_color = C_DANGER if is_esc else C_SUCCESS
        status_text  = 'ESCALADO' if is_esc else 'RESUELTO'

        # ── Bloque de incidente ──
        block = []

        # Cabecera del incidente
        inc_header = Table([[
            Paragraph(f'<b>#{inc["id"]}</b>',
                      ParagraphStyle('IH', fontName='Helvetica-Bold', fontSize=11,
                                     textColor=C_ELECTRIC, leading=14)),
            Paragraph(f'<b>{inc["error_codigo"]}</b> — {inc["error_nombre"]}',
                      ParagraphStyle('IHN', fontName='Helvetica-Bold', fontSize=10,
                                     textColor=C_WHITE, leading=13)),
            Paragraph(f'<b>{status_text}</b>',
                      ParagraphStyle('IHS', fontName='Helvetica-Bold', fontSize=9,
                                     textColor=status_color, alignment=TA_RIGHT)),
        ]], colWidths=['12%', '68%', '20%'])
        inc_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), C_BG_DARK),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROUNDEDCORNERS', [4]),
        ]))
        block.append(inc_header)
        block.append(Spacer(1, 4))

        # Datos del incidente
        paso_txt = (f'Paso {inc["paso_resolucion"]} — {inc["titulo_paso"]}'
                    if not is_esc else 'Todos los pasos agotados')

        detail_data = [
            [Paragraph('SALA', style_label), Paragraph(inc['sala'], style_val),
             Paragraph('TÉCNICO', style_label), Paragraph(inc['tecnico'], style_val)],
            [Paragraph('FECHA', style_label), Paragraph(inc['fecha'], style_val),
             Paragraph('RESOLUCIÓN', style_label), Paragraph(paso_txt, style_val)],
        ]
        if inc.get('notas'):
            detail_data.append([
                Paragraph('NOTAS', style_label),
                Paragraph(inc['notas'], ParagraphStyle('Nt2', fontName='Helvetica-Oblique',
                          fontSize=8, textColor=C_MUTED)),
                '', ''
            ])

        dt = Table(detail_data, colWidths=['14%', '36%', '14%', '36%'])
        dt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), C_PANEL),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, C_BORDER),
            ('SPAN', (1,2), (3,2)),  # notas span
        ]))
        block.append(dt)
        block.append(Spacer(1, 6))

        # ✅ MULTIPLES FOTOS: Reportes globales tambien muestran TODAS las fotografias
        all_photos = []
        if inc.get('photos') and len(inc['photos']) > 0:
            all_photos = inc['photos']
        elif inc.get('photo_url'):
            all_photos.append({
                "url": inc['photo_url'],
                "paso": inc['paso_resolucion'],
                "titulo_paso": inc['titulo_paso'],
                "fecha": inc['fecha']
            })

        if len(all_photos) > 0:
            for p_idx, photo in enumerate(all_photos, 1):
                try:
                    relative_parts = photo['url'].strip('/').split('/')
                    photo_path = os.path.join(os.getcwd(), *relative_parts)
                    if os.path.exists(photo_path):
                        img = RLImage(photo_path, width=9*cm, height=7*cm, kind='proportional')
                        img_cell = Table([[img]], colWidths=['100%'])
                        img_cell.setStyle(TableStyle([
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                            ('TOPPADDING', (0,0), (-1,-1), 8),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                            ('LEFTPADDING', (0,0), (-1,-1), 8),
                            ('BOX', (0,0), (-1,-1), 1, C_ELECTRIC_D),
                            ('BACKGROUND', (0,0), (-1,-1), C_PANEL),
                            ('ROUNDEDCORNERS', [4]),
                        ]))
                        block.append(img_cell)
                        block.append(Paragraph(f'📷 Foto {p_idx} | Paso {photo["paso"]} — {photo["titulo_paso"]}',
                                               style_caption))
                        block.append(Spacer(1, 6))
                except Exception as e:
                    block.append(Paragraph(f'[Error cargando imagen: {e}]', style_note))
        else:
            block.append(Paragraph('📷 Sin fotografía de evidencia adjunta.', style_note))

        block.append(Spacer(1, 4))
        block.append(HRFlowable(width='100%', thickness=0.5,
                                color=C_DANGER if is_esc else C_ELECTRIC_D))
        block.append(Spacer(1, 12))

        # ✅ NO USAMOS KeepTogether cuando hay multiples fotos, se rompe ReportLab
        if len(all_photos) <= 1:
            story.append(KeepTogether(block))
        else:
            # Con mas de 1 foto permitimos salto de pagina
            story.extend(block)

    # PIE DE PÁGINA FINAL
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f'CinemaCare Pro · Reporte completo generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} · '
        f'{total} incidentes · Tasa de resolución sin técnico externo: {tasa}%',
        style_footer
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer



if __name__ == '__main__':
    # ✅ Configurado para ser accesible desde cualquier dispositivo de la red local
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
