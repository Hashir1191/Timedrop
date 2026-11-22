from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import secrets
from xml.sax.saxutils import escape

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from sqlalchemy.orm import Session

from app.models import Parcel, ParcelDocument


def _safe(value: str | None) -> str:
    return escape(value or "—")


class TimeDropLogo(Flowable):
    """Centered, print-safe TimeDrop mark and separated brand tagline."""

    def __init__(self):
        super().__init__()
        self.width = 176 * mm
        self.height = 31 * mm

    def draw(self):
        c = self.canv
        c.saveState()
        navy = colors.HexColor("#102A58")
        blue = colors.HexColor("#2877F5")
        cyan = colors.HexColor("#25BDEB")
        violet = colors.HexColor("#8755F5")
        # Parcel mark
        x, y = 48 * mm, 19 * mm
        top = c.beginPath()
        top.moveTo(x + 7 * mm, y + 5 * mm)
        top.lineTo(x + 14 * mm, y + 1 * mm)
        top.lineTo(x + 7 * mm, y - 3 * mm)
        top.lineTo(x, y + 1 * mm)
        top.close()
        c.setFillColor(cyan)
        c.drawPath(top, fill=1, stroke=0)
        left = c.beginPath()
        left.moveTo(x, y + 1 * mm)
        left.lineTo(x + 7 * mm, y - 3 * mm)
        left.lineTo(x + 7 * mm, y - 11 * mm)
        left.lineTo(x, y - 7 * mm)
        left.close()
        c.setFillColor(blue)
        c.drawPath(left, fill=1, stroke=0)
        right = c.beginPath()
        right.moveTo(x + 14 * mm, y + 1 * mm)
        right.lineTo(x + 7 * mm, y - 3 * mm)
        right.lineTo(x + 7 * mm, y - 11 * mm)
        right.lineTo(x + 14 * mm, y - 7 * mm)
        right.close()
        c.setFillColor(navy)
        c.drawPath(right, fill=1, stroke=0)
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.7)
        c.line(x + 7 * mm, y + 5 * mm, x + 7 * mm, y - 3 * mm)
        c.line(x, y + 1 * mm, x + 7 * mm, y - 3 * mm)
        c.line(x + 14 * mm, y + 1 * mm, x + 7 * mm, y - 3 * mm)
        # Wordmark with measured spacing, not hard-coded glyph positions.
        font, size = "Helvetica-Bold", 29
        c.setFont(font, size)
        word_x, word_y = 66 * mm, 16 * mm
        c.setFillColor(navy)
        c.drawString(word_x, word_y, "Time")
        word_width = c.stringWidth("Time", font, size)
        c.setFillColor(blue)
        c.drawString(word_x + word_width + 2.0 * mm, word_y, "Drop")
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(navy)
        tagline = "SCHEDULE  •  TRACK  •  RECEIVE"
        tagline_width = c.stringWidth(tagline, "Helvetica-Bold", 8)
        c.drawString(word_x + 2 * mm, 5 * mm, tagline)
        c.restoreState()


class TrackingBarcode(Flowable):
    """A real Code 128 barcode for the parcel tracking number."""

    def __init__(self, tracking_number: str):
        super().__init__()
        self.value = tracking_number
        self.width = 68 * mm
        self.height = 19 * mm

    def draw(self):
        barcode = code128.Code128(self.value, barHeight=12 * mm, barWidth=0.34 * mm, humanReadable=False)
        barcode_width = barcode.width
        barcode.drawOn(self.canv, max(0, (self.width - barcode_width) / 2), 4 * mm)
        self.canv.saveState()
        self.canv.setFont("Helvetica-Bold", 7)
        self.canv.setFillColor(colors.HexColor("#102A58"))
        self.canv.drawCentredString(self.width / 2, 1 * mm, self.value)
        self.canv.restoreState()


def build_parcel_receipt(parcel: Parcel, document_number: str, verification_code: str, issued_at: datetime) -> bytes:
    buffer = BytesIO()
    navy = colors.HexColor("#102A58")
    blue = colors.HexColor("#2877F5")
    pale = colors.HexColor("#EAF3FF")
    border = colors.HexColor("#D5E3F5")
    muted = colors.HexColor("#64748B")
    ink = colors.HexColor("#172B4D")
    green = colors.HexColor("#16A34A")

    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=9 * mm, bottomMargin=12 * mm,
        title="TimeDrop Parcel Registration Receipt", author="TimeDrop",
        subject="Parcel registration confirmation",
    )
    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle("TDReceiptEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=blue)
    title = ParagraphStyle("TDReceiptTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=TA_CENTER, textColor=navy, spaceAfter=3)
    intro = ParagraphStyle("TDReceiptIntro", parent=styles["Normal"], fontSize=8.5, leading=12, alignment=TA_CENTER, textColor=muted)
    section = ParagraphStyle("TDReceiptSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=navy, spaceBefore=8, spaceAfter=5)
    label = ParagraphStyle("TDReceiptLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=muted)
    value = ParagraphStyle("TDReceiptValue", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=ink)
    prominent = ParagraphStyle("TDReceiptProminent", parent=value, fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=navy)
    white_label = ParagraphStyle("TDReceiptWhiteLabel", parent=label, textColor=colors.HexColor("#D9E8FF"), fontSize=8)
    white_value = ParagraphStyle("TDReceiptWhiteValue", parent=value, textColor=colors.white, fontName="Helvetica-Bold", fontSize=23, leading=26)
    small = ParagraphStyle("TDReceiptSmall", parent=styles["Normal"], fontSize=7.3, leading=10, textColor=muted)
    center_small = ParagraphStyle("TDReceiptCenterSmall", parent=small, alignment=TA_CENTER)

    def pair(caption: str, text: str, strong: bool = False):
        return [Paragraph(caption, label), Paragraph(text, prominent if strong else value)]

    story = [
        TimeDropLogo(),
        Table([[Paragraph("PARCEL REGISTRATION", eyebrow),
                Paragraph("CUSTOMER COPY", ParagraphStyle("TDReceiptCopy", parent=eyebrow, alignment=2))]],
              colWidths=[88 * mm, 88 * mm],
              style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, blue),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])),
        Spacer(1, 3 * mm),
        Paragraph("Parcel Registration Receipt", title),
        Paragraph("This confirms that your parcel details have been successfully registered on TimeDrop.", intro),
        Spacer(1, 4 * mm),
    ]

    metadata = Table([
        [pair("DOCUMENT REFERENCE", _safe(document_number), True),
         pair("REGISTRATION DATE", issued_at.astimezone(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC"), True)],
    ], colWidths=[88 * mm, 88 * mm], rowHeights=[17 * mm])
    metadata.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("LINEAFTER", (0, 0), (0, 0), 0.7, border),
    ]))
    story.append(metadata)
    story.append(Spacer(1, 3 * mm))

    tracking = Table([[
        [Paragraph("TRACKING NUMBER", white_label), Paragraph(_safe(parcel.tracking_number), white_value)],
        TrackingBarcode(parcel.tracking_number),
    ]], colWidths=[91 * mm, 85 * mm], rowHeights=[27 * mm])
    tracking.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), navy), ("BOX", (0, 0), (-1, -1), 0.8, navy),
        ("ROUNDEDCORNERS", [10, 10, 10, 10]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBEFORE", (1, 0), (1, 0), 0.8, colors.HexColor("#AFC8EB")),
    ]))
    story.extend([tracking, Paragraph("Recipient Details & Delivery Address", section)])

    masked_phone = "•••• " + parcel.phone[-4:] if len(parcel.phone) >= 4 else "••••"
    address = ", ".join(part for part in [parcel.address_line, parcel.city, parcel.state] if part)
    address = f"{address}, {parcel.pincode}" if parcel.pincode else address
    recipient = Table([
        [[Paragraph("RECIPIENT DETAILS", ParagraphStyle("TDRecipientHead", parent=label, textColor=navy, fontSize=8)),
          Paragraph(_safe(parcel.recipient_name), prominent),
          Paragraph("MOBILE  " + _safe(masked_phone), value)],
         [Paragraph("DELIVERY ADDRESS", ParagraphStyle("TDAddressHead", parent=label, textColor=navy, fontSize=8)),
          Paragraph(_safe(address), value)],
    ], colWidths=[88 * mm, 88 * mm], rowHeights=[31 * mm])
    recipient.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale), ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, border), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([recipient, Paragraph("Document Verification", section)])

    verification = Table([[
        [Paragraph("VERIFICATION CODE", label), Paragraph(_safe(verification_code), prominent)],
        Paragraph("This code identifies this issued document. Keep it with your receipt for reference.", small),
    ]], colWidths=[82 * mm, 94 * mm], rowHeights=[20 * mm])
    verification.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale), ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("LINEBEFORE", (1, 0), (1, 0), 0.7, border),
    ]))
    story.extend([verification, Paragraph("Next Steps", section)])

    stages = [
        ("1", "Parcel Registered", "Completed"),
        ("2", "Partner Assigned", "Pending"),
        ("3", "Out for Delivery", "Pending"),
        ("4", "Delivered", "Pending"),
    ]
    current = (parcel.status or "registered").lower()
    stage_map = {
        "registered": 0, "received": 1, "assigned": 1, "accepted": 1,
        "out_for_delivery": 2, "delivered": 3,
    }
    active_stage = stage_map.get(current, 0)
    timeline_cells = []
    for index, (number, name, _) in enumerate(stages):
        is_done = index <= active_stage
        color = green if index < active_stage or (index == 0 and current == "registered") else blue
        status_text = "Completed" if is_done else "Pending"
        timeline_cells.append([
            Paragraph(f'<font color="{color.hexval()}"><b>{number}</b></font>', ParagraphStyle(f"TDStepNum{index}", parent=center_small, fontSize=13, leading=15)),
            Paragraph(f"<b>{name}</b>", ParagraphStyle(f"TDStepName{index}", parent=center_small, textColor=navy, fontSize=7.5, leading=9)),
            Paragraph(status_text, ParagraphStyle(f"TDStepState{index}", parent=center_small, textColor=green if is_done else muted, fontSize=7, leading=9)),
        ])
    timeline = Table([timeline_cells], colWidths=[44 * mm] * 4, rowHeights=[20 * mm])
    timeline.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([timeline, Spacer(1, 4 * mm)])

    notice = Table([[Paragraph(
        "<b>Please note</b><br/>This is a parcel registration receipt only. It confirms that the parcel details were recorded in TimeDrop. "
        "It does not confirm physical receipt by a warehouse or delivery partner. Final delivery is confirmed separately when the delivery is completed.",
        small)]], colWidths=[176 * mm])
    notice.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale), ("BOX", (0, 0), (-1, -1), 0.7, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        notice, Spacer(1, 4 * mm),
        Paragraph("Generated by TimeDrop  •  Smart Parcel Delivery", center_small),
    ])
    doc.build(story)
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
