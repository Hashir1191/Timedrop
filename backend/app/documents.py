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
    """Vector TimeDrop wordmark for crisp printing at any PDF resolution."""

    def __init__(self):
        super().__init__()
        self.width = 174 * mm
        self.height = 24 * mm

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        navy = colors.HexColor("#102A58")
        blue = colors.HexColor("#2877F5")
        cyan = colors.HexColor("#25BDEB")
        violet = colors.HexColor("#8755F5")

        # Parcel mark: three clean faces and a small location pin.
        x, y, unit = 4 * mm, 3 * mm, 1 * mm
        parcel = canvas.beginPath()
        parcel.moveTo(x + 13 * unit, y + 21 * unit)
        parcel.lineTo(x + 26 * unit, y + 14 * unit)
        parcel.lineTo(x + 13 * unit, y + 7 * unit)
        parcel.lineTo(x, y + 14 * unit)
        parcel.close()
        canvas.setFillColor(cyan)
        canvas.drawPath(parcel, fill=1, stroke=0)

        left = canvas.beginPath()
        left.moveTo(x, y + 14 * unit)
        left.lineTo(x + 13 * unit, y + 7 * unit)
        left.lineTo(x + 13 * unit, y - 7 * unit)
        left.lineTo(x, y)
        left.close()
        canvas.setFillColor(blue)
        canvas.drawPath(left, fill=1, stroke=0)

        right = canvas.beginPath()
        right.moveTo(x + 26 * unit, y + 14 * unit)
        right.lineTo(x + 13 * unit, y + 7 * unit)
        right.lineTo(x + 13 * unit, y - 7 * unit)
        right.lineTo(x + 26 * unit, y)
        right.close()
        canvas.setFillColor(navy)
        canvas.drawPath(right, fill=1, stroke=0)

        canvas.setStrokeColor(colors.white)
        canvas.setLineWidth(0.8)
        canvas.line(x + 13 * unit, y + 21 * unit, x + 13 * unit, y + 7 * unit)
        canvas.line(x, y + 14 * unit, x + 13 * unit, y + 7 * unit)
        canvas.line(x + 26 * unit, y + 14 * unit, x + 13 * unit, y + 7 * unit)

        pin_x, pin_y = x + 28 * unit, y + 21 * unit
        canvas.setFillColor(violet)
        canvas.circle(pin_x, pin_y, 4 * unit, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.circle(pin_x, pin_y, 1.3 * unit, fill=1, stroke=0)

        canvas.setFillColor(navy)
        canvas.setFont("Helvetica-Bold", 23)
        canvas.drawString(38 * mm, 11 * mm, "Time")
        canvas.setFillColor(blue)
        canvas.drawString(59 * mm, 11 * mm, "Drop")
        canvas.setFillColor(colors.HexColor("#6B7C98"))
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.drawString(38.5 * mm, 5 * mm, "S M A R T   P A R C E L   D E L I V E R Y")
        canvas.restoreState()


def build_parcel_receipt(parcel: Parcel, document_number: str, verification_code: str, issued_at: datetime) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="TimeDrop Parcel Registration Receipt",
        author="TimeDrop",
        subject="Verifiable parcel registration receipt",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReceiptTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=colors.HexColor("#18365b"), alignment=TA_LEFT, spaceAfter=5)
    subtitle = ParagraphStyle("ReceiptSubtitle", parent=styles["Normal"], fontSize=9, leading=14, textColor=colors.HexColor("#64748b"))
    section = ParagraphStyle("ReceiptSection", parent=styles["Heading2"], fontSize=11, leading=15, textColor=colors.HexColor("#244b7a"), spaceBefore=12, spaceAfter=7)
    label = ParagraphStyle("ReceiptLabel", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#718096"))
    value = ParagraphStyle("ReceiptValue", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#26364b"))
    strong = ParagraphStyle("ReceiptStrong", parent=value, fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=colors.HexColor("#1f3f6b"))
    centered = ParagraphStyle("ReceiptCenter", parent=subtitle, alignment=TA_CENTER)

    story = [
        TimeDropLogo(),
        Paragraph("PARCEL REGISTRATION RECEIPT", section),
        Paragraph("Your parcel has been registered in the TimeDrop system. Keep this document as your proof of registration.", subtitle),
        Spacer(1, 9 * mm),
    ]
    summary = [
        [Paragraph("TRACKING NUMBER", label), Paragraph("DOCUMENT NUMBER", label)],
        [Paragraph(_safe(parcel.tracking_number), strong), Paragraph(_safe(document_number), value)],
        [Paragraph("REGISTRATION DATE", label), Paragraph("CURRENT STATUS", label)],
        [Paragraph(issued_at.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC"), value), Paragraph(_safe(parcel.status.replace("_", " ").title()), value)],
    ]
    table = Table(summary, colWidths=[85 * mm, 85 * mm], rowHeights=[8 * mm, 12 * mm, 8 * mm, 12 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f8fc")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbe5f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e4ebf3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([table, Paragraph("Recipient and destination", section)])
    masked_phone = "**** " + parcel.phone[-4:] if len(parcel.phone) >= 4 else "••••"
    details = [
        [Paragraph("RECIPIENT", label), Paragraph("CONTACT", label)],
        [Paragraph(_safe(parcel.recipient_name), value), Paragraph(_safe(masked_phone), value)],
        [Paragraph("DELIVERY ADDRESS", label), Paragraph("PIN CODE", label)],
        [Paragraph(_safe(parcel.address_line + ", " + parcel.city + ", " + parcel.state), value), Paragraph(_safe(parcel.pincode), value)],
    ]
    detail_table = Table(details, colWidths=[125 * mm, 45 * mm], rowHeights=[8 * mm, 12 * mm, 8 * mm, 18 * mm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbe5f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e4ebf3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([detail_table, Paragraph("Verification", section)])
    verification = [
        [Paragraph("VERIFICATION CODE", label), Paragraph("ISSUED BY", label)],
        [Paragraph(_safe(verification_code), strong), Paragraph("TimeDrop Parcel Services", value)],
    ]
    verification_table = Table(verification, colWidths=[85 * mm, 85 * mm], rowHeights=[8 * mm, 13 * mm])
    verification_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f8fc")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbe5f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([
        verification_table,
        Spacer(1, 7 * mm),
        Paragraph("This receipt confirms that the parcel details above were registered in TimeDrop. It is not proof that the parcel was physically received by a warehouse or delivery partner, and it is not proof of final delivery.", subtitle),
        Spacer(1, 4 * mm),
        Paragraph("Verify this document using its verification code in the TimeDrop document verification service.", centered),
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
