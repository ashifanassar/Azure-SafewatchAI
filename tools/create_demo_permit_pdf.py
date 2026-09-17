from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT = Path("output/pdf/permit-demo-001.pdf")


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#17324d"),
        spaceAfter=8,
    )
    section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#17324d"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9, leading=12)

    rows = [
        ["Permit Number", "PTW-001"],
        ["Document Type", "Permit to Work"],
        ["Work Type", "Work at Height"],
        ["Status", "Valid"],
        ["Site ID", "site-001"],
        ["Zone ID", "zone-04"],
        ["Contractor ID", "contractor-001"],
        ["Issued To", "SafeWatch Demo Contractor"],
        ["Valid From", "2026-08-21T08:00:00Z"],
        ["Expiry At", "2026-12-31T18:00:00Z"],
    ]
    table = Table(rows, colWidths=[45 * mm, 100 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e9f0f7")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#17324d")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b7c4d1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    controls = [
        ["Hazard", "Control Requirement"],
        ["Work at height", "Full body harness must be worn and anchored before accessing scaffold."],
        ["Scaffold access", "Access platform must be inspected before work starts."],
        ["Permit control", "Supervisor must verify permit validity before work begins."],
    ]
    controls_table = Table(controls, colWidths=[45 * mm, 100 * mm])
    controls_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b7c4d1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story = [
        Paragraph("SafeWatch AI Demo Permit", title),
        Paragraph("Permit-to-work document for validating the Phase 2 Document Agent.", body),
        Spacer(1, 8),
        Paragraph("Permit Details", section),
        table,
        Paragraph("Safety Controls", section),
        controls_table,
        Paragraph("Approval", section),
        Paragraph("Approved By: HSE Supervisor<br/>Approval Status: Approved<br/>Signature: Demo Document", body),
    ]
    doc.build(story)


if __name__ == "__main__":
    build()
