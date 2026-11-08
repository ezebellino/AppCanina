"""A portable, two-sided animal credential. Issuance/permissions stay in views."""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

SIZE = (420, 298)  # A6 landscape, comfortable to read on screen or print.
INK = HexColor("#123D34")
MUTED = HexColor("#526F65")
GREEN = HexColor("#075448")


def _text(pdf, text, x, top, width, height, size=11, bold=False, color=INK):
    """Wrap long names and shrink within a reserved area without clipping."""
    for font_size in range(size, 5, -1):
        style = ParagraphStyle("field", fontName="Helvetica-Bold" if bold else "Helvetica",
                               fontSize=font_size, leading=font_size * 1.2, textColor=color)
        paragraph = Paragraph(escape(str(text)), style)
        _, used_height = paragraph.wrap(width, height)
        if used_height <= height:
            break
    paragraph.drawOn(pdf, x, top - used_height)


def build_credential_pdf(patient, contact, code, expires_at):
    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=SIZE)
    pdf.setTitle(f"Credencial veterinaria - {patient.name}")
    pdf.setAuthor("AppCanina")
    expiry = timezone.localtime(expires_at).strftime("%d/%m/%Y %H:%M")

    def background(side):
        pdf.setFillColor(HexColor("#F0F8F4"))
        pdf.rect(0, 0, *SIZE, fill=1, stroke=0)
        pdf.setFillColor(GREEN)
        pdf.rect(0, 242, 420, 56, fill=1, stroke=0)
        _text(pdf, "AppCanina", 20, 282, 160, 22, 17, True, HexColor("#FFFFFF"))
        _text(pdf, "CREDENCIAL VETERINARIA DE VIAJE", 20, 259, 350, 14, 8, False, HexColor("#C9E9DE"))
        _text(pdf, side, 350, 280, 50, 14, 8, False, HexColor("#C9E9DE"))

    background("FRENTE")
    pdf.setFillColor(HexColor("#DFEDE5"))
    pdf.roundRect(20, 78, 130, 148, 12, fill=1, stroke=0)
    photo = None
    if patient.photo:
        try:
            with patient.photo.open("rb") as source:
                with Image.open(source) as original:
                    photo = ImageOps.exif_transpose(original).convert("RGB")
                    photo.thumbnail((800, 1000))
        except (OSError, ValueError):
            photo = None
    if photo is not None:
        pdf.drawImage(ImageReader(photo), 26, 84, 118, 136, preserveAspectRatio=True, anchor="c", mask="auto")
    else:
        _text(pdf, "Sin foto", 49, 159, 80, 30, 12, color=MUTED)
    _text(pdf, patient.name, 167, 227, 233, 56, 23, True)
    _text(pdf, "ESPECIE / RAZA", 167, 163, 230, 12, 8, color=MUTED)
    _text(pdf, f"{patient.get_species_display()} / {patient.breed or 'Sin informar'}", 167, 149, 233, 35)
    _text(pdf, "NACIMIENTO", 167, 108, 230, 12, 8, color=MUTED)
    _text(pdf, patient.birth_date.strftime("%d/%m/%Y") if patient.birth_date else "Sin informar", 167, 94, 230, 18)
    _text(pdf, "RESPONSABLE", 20, 66, 240, 12, 8, color=MUTED)
    _text(pdf, contact.full_name, 20, 52, 245, 35, 11, True)
    _text(pdf, "CÓDIGO VÁLIDO HASTA", 285, 66, 115, 12, 8, color=MUTED)
    _text(pdf, expiry, 285, 50, 115, 30, 10, True)
    pdf.showPage()

    background("DORSO")
    _text(pdf, "IDENTIFICACIÓN / MICROCHIP", 20, 226, 380, 12, 8, color=MUTED)
    _text(pdf, patient.microchip or "Sin informar", 20, 211, 380, 32, 11, True)
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.roundRect(20, 112, 380, 62, 10, fill=1, stroke=0)
    _text(pdf, "CÓDIGO TEMPORAL", 34, 162, 350, 12, 8, color=MUTED)
    pdf.setFillColor(INK)
    pdf.setFont("Courier-Bold", 13)
    pdf.drawString(34, 131, code)
    _text(pdf, f"Vigencia: hasta {expiry} (hora de Argentina).", 20, 101, 380, 18, 10, True)
    _text(pdf, "Presentá esta tarjeta en la veterinaria. La consulta del historial requiere tu consentimiento y la validación del equipo profesional.", 20, 77, 380, 34, 10)
    _text(pdf, "La credencial no reemplaza la libreta sanitaria ni certifica vacunas. Guardá el código de forma privada.", 20, 34, 380, 26, 8, color=MUTED)
    pdf.save()
    return buffer.getvalue()
