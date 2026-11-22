from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import re
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
        c.drawString(word_x + word_width, word_y, "Drop")
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
        scale = min(1.0, self.width / barcode_width) if barcode_width else 1.0
        self.canv.saveState()
        self.canv.translate(max(0, (self.width - barcode_width * scale) / 2), 4 * mm)
        self.canv.scale(scale, scale)
        barcode.drawOn(self.canv, 0, 0)
        self.canv.restoreState()
        self.canv.saveState()
        self.canv.setFont("Helvetica-Bold", 7)
        self.canv.setFillColor(colors.HexColor("#102A58"))
        self.canv.drawCentredString(self.width / 2, 1 * mm, self.value)
        self.canv.restoreState()


def build_parcel_receipt(parcel: Parcel, document_number: str, verification_code: str, issued_at: datetime) -> bytes:
    """Build a premium, print-friendly one-page customer registration receipt."""
    buffer = BytesIO()
    navy = colors.HexColor("#102A58")
    deep = colors.HexColor("#0B1D3A")
    blue = colors.HexColor("#2877F5")
    pale = colors.HexColor("#F3F7FD")
    border = colors.HexColor("#DCE6F2")
    ink = colors.HexColor("#172B4D")
    muted = colors.HexColor("#687B96")
    green = colors.HexColor("#14966B")
    white = colors.white

    page_width, page_height = A4

    def page_chrome(canvas, document):
        canvas.saveState()
        canvas.setFillColor(blue)
        canvas.rect(0, page_height - 2.2 * mm, page_width, 2.2 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(border)
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, 10 * mm, page_width - 15 * mm, 10 * mm)
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(muted)
        canvas.drawString(15 * mm, 6 * mm, "TIMEDROP  /  SMART PARCEL DELIVERY")
        canvas.drawRightString(page_width - 15 * mm, 6 * mm, "KEEP THIS RECEIPT FOR YOUR RECORDS")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=8 * mm, bottomMargin=14 * mm,
        title="TimeDrop Premium Parcel Registration Receipt",
        author="TimeDrop", subject="Parcel registration confirmation",
    )
    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle("TDPremiumEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=blue, spaceAfter=2)
    title = ParagraphStyle("TDPremiumTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=deep, alignment=0, spaceAfter=2)
    intro = ParagraphStyle("TDPremiumIntro", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=muted)
    section = ParagraphStyle("TDPremiumSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=navy, spaceBefore=7, spaceAfter=4)
    label = ParagraphStyle("TDPremiumLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=6.5, leading=8, textColor=muted)
    value = ParagraphStyle("TDPremiumValue", parent=styles["Normal"], fontSize=9, leading=12, textColor=ink)
    value_bold = ParagraphStyle("TDPremiumValueBold", parent=value, fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=navy)
    small = ParagraphStyle("TDPremiumSmall", parent=styles["Normal"], fontSize=7, leading=9.5, textColor=muted)
    small_center = ParagraphStyle("TDPremiumSmallCenter", parent=small, alignment=TA_CENTER)
    white_label = ParagraphStyle("TDPremiumWhiteLabel", parent=label, textColor=colors.HexColor("#BFD5F5"), fontSize=7)
    tracking_value = ParagraphStyle("TDPremiumTracking", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=white)

    def field(caption: str, text: str, strong: bool = False):
        return [Paragraph(caption, label), Paragraph(text, value_bold if strong else value)]

    local_issued = issued_at.astimezone(timezone.utc).strftime("%d %b %Y  ·  %H:%M UTC")
    masked_phone = "•••• " + parcel.phone[-4:] if len(parcel.phone) >= 4 else "••••"
    address_parts = [re.sub(r"\\s*,\\s*", ", ", part.strip()) for part in [parcel.address_line, parcel.city, parcel.state] if part and part.strip()]
    address = ", ".join(address_parts)
    address = re.sub(r"\\s+", " ", address).strip()
    address = f"{address}, {parcel.pincode.strip()}" if parcel.pincode and parcel.pincode.strip() else address
    address = _safe(address)
    current = (parcel.status or "registered").lower()
    stage_map = {
        "registered": 0, "received": 1, "assigned": 1, "accepted": 1,
        "out_for_delivery": 2, "delivered": 3,
    }
    active_stage = stage_map.get(current, 0)

    story = [
        TimeDropLogo(),
        Spacer(1, 1 * mm),
        Paragraph("PARCEL REGISTRATION", eyebrow),
        Paragraph("Your parcel is in the system.", title),
        Paragraph("Your registration is confirmed. Use the tracking reference below whenever you need an update.", intro),
        Spacer(1, 4 * mm),
    ]

    barcode = TrackingBarcode(parcel.tracking_number)
    barcode.width = 65 * mm
    barcode.height = 18 * mm
    barcode_panel = [
        Paragraph("SCAN BARCODE", ParagraphStyle("TDPremiumBarcodeLabel", parent=label, alignment=TA_CENTER)),
        barcode,
    ]
    hero = Table([[
        [Paragraph("YOUR TRACKING NUMBER", white_label),
         Paragraph(_safe(parcel.tracking_number), tracking_value),
         Paragraph(f"Registered  ·  {local_issued}", ParagraphStyle("TDPremiumHeroMeta", parent=small, textColor=colors.HexColor("#C7D8F0"), fontSize=7.2))],
        barcode_panel,
    ]], colWidths=[95 * mm, 85 * mm], rowHeights=[34 * mm])
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), deep), ("BACKGROUND", (1, 0), (1, 0), white),
        ("BOX", (0, 0), (-1, -1), 0.8, deep), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBEFORE", (1, 0), (1, 0), 0.8, border),
    ]))
    story.extend([hero, Spacer(1, 3 * mm)])

    metadata = Table([[
        field("DOCUMENT NUMBER", _safe(document_number), True),
        field("ISSUED ON", local_issued.upper(), True),
        field("PARCEL STATUS", _safe(current.replace("_", " ").upper()), True),
    ]], colWidths=[60 * mm, 66 * mm, 54 * mm], rowHeights=[15 * mm])
    metadata.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale), ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([metadata, Paragraph("Delivery details", section)])

    recipient = Table([[
        [Paragraph("RECIPIENT", label), Spacer(1, 1.5 * mm),
         Paragraph(_safe(parcel.recipient_name), ParagraphStyle("TDPremiumRecipient", parent=value_bold, fontSize=13, leading=16)),
         Spacer(1, 1 * mm), Paragraph("CONTACT NUMBER", label), Paragraph(_safe(masked_phone), value)],
        [Paragraph("DELIVERY ADDRESS", label), Spacer(1, 1.5 * mm),
         Paragraph(address, ParagraphStyle("TDPremiumAddress", parent=value, fontSize=9.5, leading=14)),
         Spacer(1, 2 * mm), Paragraph("POSTAL PIN CODE", label), Paragraph(_safe(parcel.pincode), value)],
    ]], colWidths=[90 * mm, 90 * mm], rowHeights=[33 * mm])
    recipient.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white), ("BOX", (0, 0), (-1, -1), 0.7, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, border), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([recipient, Paragraph("Delivery journey", section)])

    journey = []
    stages = ["Registered", "Partner assigned", "Out for delivery", "Delivered"]
    for index, name in enumerate(stages):
        complete = index <= active_stage
        symbol = "✓" if complete else "○"
        icon_color = green if complete else border
        state_text = "COMPLETE" if complete else "UP NEXT"
        journey.append([
            Paragraph(f'<font color="{icon_color.hexval()}"><b>{symbol}</b></font>',
                      ParagraphStyle(f"TDPremiumJourneyIcon{index}", parent=small_center, fontSize=15, leading=17)),
            Paragraph(f"<b>{name}</b>",
                      ParagraphStyle(f"TDPremiumJourneyName{index}", parent=small_center, textColor=navy if complete else muted, fontSize=7.2, leading=9)),
            Paragraph(state_text,
                      ParagraphStyle(f"TDPremiumJourneyState{index}", parent=small_center, textColor=green if complete else muted, fontName="Helvetica-Bold", fontSize=6, leading=8)),
        ])
    journey_table = Table([journey], colWidths=[45 * mm] * 4, rowHeights=[18 * mm])
    journey_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale), ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBEFORE", (1, 0), (-1, -1), 0.5, border),
    ]))
    story.extend([journey_table, Paragraph("Document authenticity", section)])

    verification = Table([[
        [Paragraph("VERIFICATION CODE", label), Spacer(1, 1 * mm),
         Paragraph(_safe(verification_code), ParagraphStyle("TDPremiumVerifyCode", parent=value_bold, fontSize=8.3, leading=11)),
         Paragraph("Use this code with the TimeDrop document verification service.", small)],
        [Paragraph("ISSUED BY", label), Spacer(1, 1 * mm),
         Paragraph("TimeDrop Parcel Services", value_bold),
         Paragraph("Original document reference retained", small)],
    ]], colWidths=[105 * mm, 75 * mm], rowHeights=[22 * mm])
    verification.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFE")),
        ("BOX", (0, 0), (-1, -1), 0.7, border), ("INNERGRID", (0, 0), (-1, -1), 0.5, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([verification, Spacer(1, 3 * mm)])

    notice = Table([[Paragraph(
        "<b>IMPORTANT INFORMATION</b><br/>This receipt confirms that the parcel details above were registered in TimeDrop. "
        "It does not confirm physical receipt by a warehouse or delivery partner, and it is not proof of final delivery.",
        small)]], colWidths=[180 * mm])
    notice.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9ED")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#F0D9A8")),
        ("LINEBEFORE", (0, 0), (0, 0), 2, colors.HexColor("#E5A63B")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([notice, Spacer(1, 2 * mm), Paragraph("Thank you for choosing TimeDrop.", small_center)])
    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
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
