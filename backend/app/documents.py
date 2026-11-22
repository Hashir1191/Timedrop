from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import secrets
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from sqlalchemy.orm import Session

from app.models import Parcel, ParcelDocument


def _safe(value: str | None) -> str:
    return escape(value or "—")


class TimeDropLogo(Flowable):
    """Vector TimeDrop wordmark with measured spacing for reliable PDF rendering."""

    def __init__(self):
        super().__init__()
        self.width = 174 * mm
        self.height = 27 * mm

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        navy = colors.HexColor("#102A58")
        blue = colors.HexColor("#2877F5")
        cyan = colors.HexColor("#25BDEB")
        violet = colors.HexColor("#8755F5")
        x, y, unit = 4 * mm, 12 * mm, 1 * mm

        top = canvas.beginPath()
        top.moveTo(x + 12 * unit, y + 7 * unit)
        top.lineTo(x + 24 * unit, y + 1 * unit)
        top.lineTo(x + 12 * unit, y - 5 * unit)
        top.lineTo(x, y + 1 * unit)
        top.close()
        canvas.setFillColor(cyan)
        canvas.drawPath(top, fill=1, stroke=0)
        left = canvas.beginPath()
        left.moveTo(x, y + 1 * unit)
        left.lineTo(x + 12 * unit, y - 5 * unit)
        left.lineTo(x + 12 * unit, y - 15 * unit)
        left.lineTo(x, y - 9 * unit)
        left.close()
        canvas.setFillColor(blue)
        canvas.drawPath(left, fill=1, stroke=0)
        right = canvas.beginPath()
        right.moveTo(x + 24 * unit, y + 1 * unit)
        right.lineTo(x + 12 * unit, y - 5 * unit)
        right.lineTo(x + 12 * unit, y - 15 * unit)
        right.lineTo(x + 24 * unit, y - 9 * unit)
        right.close()
        canvas.setFillColor(navy)
        canvas.drawPath(right, fill=1, stroke=0)
        canvas.setStrokeColor(colors.white)
        canvas.setLineWidth(0.8)
        canvas.line(x + 12 * unit, y + 7 * unit, x + 12 * unit, y - 5 * unit)
        canvas.line(x, y + 1 * unit, x + 12 * unit, y - 5 * unit)
        canvas.line(x + 24 * unit, y + 1 * unit, x + 12 * unit, y - 5 * unit)
        canvas.setFillColor(violet)
        canvas.circle(x + 29 * unit, y + 7 * unit, 3.2 * unit, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.circle(x + 29 * unit, y + 7 * unit, 1.1 * unit, fill=1, stroke=0)

        font_size = 22
        canvas.setFont("Helvetica-Bold", font_size)
        word_x = 38 * mm
        canvas.setFillColor(navy)
        canvas.drawString(word_x, 10 * mm, "Time")
        time_width = canvas.stringWidth("Time", "Helvetica-Bold", font_size)
        canvas.setFillColor(blue)
        canvas.drawString(word_x + time_width + 2.2 * mm, 10 * mm, "Drop")
        canvas.setFillColor(colors.HexColor("#6B7C98"))
        canvas.setFont("Helvetica-Bold", 6.2)
        canvas.drawString(word_x + 0.5 * mm, 4 * mm, "SMART PARCEL DELIVERY")
        canvas.restoreState()


def build_parcel_receipt(parcel: Parcel, document_number: str, verification_code: str, issued_at: datetime) -> bytes:
    buffer = BytesIO()
    navy = colors.HexColor("#102A58")
    blue = colors.HexColor("#2877F5")
    pale = colors.HexColor("#F1F6FD")
    border = colors.HexColor("#D9E4F2")
    muted = colors.HexColor("#64748B")
    ink = colors.HexColor("#1E2F49")

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="TimeDrop Parcel Registration Receipt",
        author="TimeDrop",
        subject="Verifiable parcel registration receipt",
    )
    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle("TDReceiptEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=blue, spaceAfter=3)
    heading = ParagraphStyle("TDReceiptHeading", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, alignment=TA_LEFT, textColor=navy, spaceAfter=4)
    intro = ParagraphStyle("TDReceiptIntro", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=muted)
    section = ParagraphStyle("TDReceiptSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=navy, spaceBefore=11, spaceAfter=6)
    label = ParagraphStyle("TDReceiptLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=muted)
    value = ParagraphStyle("TDReceiptValue", parent=styles["Normal"], fontSize=9, leading=12, textColor=ink)
    key_value = ParagraphStyle("TDReceiptKeyValue", parent=value, fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=navy)
    small = ParagraphStyle("TDReceiptSmall", parent=styles["Normal"], fontSize=7.5, leading=10.5, textColor=muted)
    center = ParagraphStyle("TDReceiptCenter", parent=small, alignment=TA_CENTER)

    def cell(label_text: str, value_text: str, prominent: bool = False):
        return [Paragraph(label_text, label), Paragraph(value_text, key_value if prominent else value)]

    story = [
        TimeDropLogo(),
        Spacer(1, 3 * mm),
        Table([[Paragraph("PARCEL SERVICES  /  CUSTOMER COPY", eyebrow),
                Paragraph("REGISTRATION RECEIPT", ParagraphStyle("TDReceiptTag", parent=label, alignment=2, textColor=blue))]],
              colWidths=[112 * mm, 54 * mm],
              style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LINEBELOW", (0, 0), (-1, -1), 1.2, blue),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 5)])),
        Spacer(1, 4 * mm),
        Paragraph("Your parcel is registered.", heading),
        Paragraph("Keep this receipt for your records. It contains the reference details associated with your parcel registration.", intro),
        Spacer(1, 5 * mm),
    ]

    summary = Table([
        [cell("TRACKING NUMBER", _safe(parcel.tracking_number), True),
         cell("DOCUMENT REFERENCE", _safe(document_number))],
        [cell("REGISTERED ON", issued_at.astimezone(timezone.utc).strftime("%d %b %Y  •  %H:%M UTC")),
         cell("CURRENT STATUS", _safe(parcel.status.replace("_", " ").title()))],
    ], colWidths=[83 * mm, 83 * mm], rowHeights=[19 * mm, 17 * mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale), ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary, Paragraph("Recipient & delivery destination", section)])

    masked_phone = "•••• " + parcel.phone[-4:] if len(parcel.phone) >= 4 else "••••"
    address = ", ".join(part for part in [parcel.address_line, parcel.city, parcel.state] if part)
    recipient = Table([
        [cell("RECIPIENT NAME", _safe(parcel.recipient_name)), cell("CONTACT NUMBER", _safe(masked_phone))],
        [cell("DELIVERY ADDRESS", _safe(address)), cell("POSTAL PIN CODE", _safe(parcel.pincode))],
    ], colWidths=[120 * mm, 46 * mm], rowHeights=[17 * mm, 23 * mm])
    recipient.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, border), ("INNERGRID", (0, 0), (-1, -1), 0.5, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([recipient, Paragraph("Document verification", section)])

    verify = Table([
        [cell("VERIFICATION CODE", _safe(verification_code), True),
         cell("ISSUED BY", "TimeDrop")],
    ], colWidths=[83 * mm, 83 * mm], rowHeights=[19 * mm])
    verify.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale), ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    notice = Table([[Paragraph(
        "<b>Important:</b> This receipt confirms that parcel details were recorded in TimeDrop. "
        "It does not confirm physical receipt by a warehouse or delivery partner, and it is not proof of final delivery.",
        small)]], colWidths=[166 * mm])
    notice.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF8E8")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#F1D9A8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        verify, Spacer(1, 7 * mm), notice, Spacer(1, 6 * mm),
        Paragraph("Need help? Keep your tracking number handy when contacting the official TimeDrop support channel.", center),
        Spacer(1, 3 * mm),
        Paragraph("Generated by TimeDrop  •  Smart Parcel Delivery", center),
    ])
    document.build(story)
    return buffer.getvalue()

def create_parcel_registration_receipt(db: Session, parcel: Parcel, generated_by_id: int) -> ParcelDocument:
    issued_at = datetime.now(timezone.utc)
    document_number = "TD-R-" + secrets.token_hex(4).upper()
    verification_code = "TDV-" + secrets.token_hex(16).upper()
    content = build_parcel_receipt(parcel, document_number, verification_code, issued_at)
    record = ParcelDocument(
        parcel_id=parcel.id,
        document_type="parcel_registration",
        document_number=document_number,
        verification_code=verification_code,
        sha256=sha256(content).hexdigest(),
        pdf_content=content,
        generated_by_id=generated_by_id,
        created_at=issued_at,
    )
    db.add(record)
    db.flush()
    return record
