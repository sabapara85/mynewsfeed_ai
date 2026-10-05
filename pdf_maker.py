"""ReportLab PDF builder — branded, paginated, report-type aware."""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

NAVY = colors.HexColor("#0B1F3A")
ACCENT = colors.HexColor("#2563EB")
GREEN = colors.HexColor("#047857")
AMBER = colors.HexColor("#B45309")
PURPLE = colors.HexColor("#6D28D9")
GREY = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F1F5F9")

DEVELOPER = "Viral Patel"


def _styles():
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20,
                                leading=24, textColor=colors.white),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=9.5,
                                   leading=13, textColor=colors.HexColor("#CBD5E1")),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=11,
                                  leading=14, textColor=colors.white),
        "num": ParagraphStyle("num", fontName="Helvetica-Bold", fontSize=9,
                              leading=13, textColor=ACCENT),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                               leading=13.5, textColor=colors.HexColor("#1E293B")),
        "outlook": ParagraphStyle("outlook", fontName="Helvetica", fontSize=10,
                                  leading=15, textColor=colors.HexColor("#1E293B")),
        "disclaimer": ParagraphStyle("disclaimer", fontName="Helvetica-Oblique",
                                     fontSize=7.5, leading=10, textColor=GREY),
    }


def _header_block(data, styles, width):
    left = [
        Paragraph("DAILY BRIEFING", styles["title"]),
        Spacer(1, 3),
        Paragraph(
            f"{data['report_label']} &nbsp;•&nbsp; {data['session']} Edition "
            f"&nbsp;•&nbsp; {data['date']} &nbsp;•&nbsp; "
            f"Generated {data['generated_at']} IST",
            styles["subtitle"],
        ),
    ]
    inner = Table([[left]], colWidths=[width - 16 * mm])
    inner.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    band = Table([[inner]], colWidths=[width])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 7 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7 * mm),
    ]))
    return band


def _section_header(text, color, styles, width):
    t = Table([[Paragraph(text, styles["section"])]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _numbered_list(lines, styles, width):
    rows = []
    for i, line in enumerate(lines, start=1):
        rows.append([
            Paragraph(f"{i:02d}", styles["num"]),
            Paragraph(line, styles["body"]),
        ])
    t = Table(rows, colWidths=[9 * mm, width - 9 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#E2E8F0")),
    ]))
    return t


def _outlook_box(text, styles, width):
    t = Table([[Paragraph(text, styles["outlook"])]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _footer_factory(label, session, date_str):
    def _footer(canvas, doc):
        canvas.saveState()
        w, _ = A4
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 16 * mm, w - 18 * mm, 16 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(18 * mm, 11.5 * mm, f"Developed by {DEVELOPER}")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY)
        canvas.drawCentredString(w / 2, 11.5 * mm, f"{label} • {session} • {date_str}")
        canvas.drawRightString(w - 18 * mm, 11.5 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return _footer


def build_pdf(data: dict) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=22 * mm,
        title=f"{data.get('report_label', 'Daily Briefing')} — {data['date']}",
        author=DEVELOPER,
    )
    width = doc.width
    styles = _styles()
    report_type = data.get("type", "general")

    story = [
        _header_block(data, styles, width),
        Spacer(1, 8 * mm),
    ]

    if report_type == "general":
        story += [
            _section_header("GENERAL AWARENESS", NAVY, styles, width),
            Spacer(1, 2 * mm),
            _numbered_list(data.get("general_summary", []), styles, width),
        ]
    elif report_type == "economic":
        story += [
            _section_header("INVESTMENT IMPACT", ACCENT, styles, width),
            Spacer(1, 2 * mm),
            _numbered_list(data.get("investment_summary", []), styles, width),
            Spacer(1, 7 * mm),
            KeepTogether([
                _section_header("INDIA MARKET OUTLOOK", GREEN, styles, width),
                Spacer(1, 2 * mm),
                _outlook_box(data.get("india_market_outlook", "unclear"), styles, width),
            ]),
            Spacer(1, 6 * mm),
            KeepTogether([
                _section_header("USA MARKET OUTLOOK", PURPLE, styles, width),
                Spacer(1, 2 * mm),
                _outlook_box(data.get("usa_market_outlook", "unclear"), styles, width),
            ]),
        ]

    story += [
        Spacer(1, 8 * mm),
        Paragraph(
            "Generated by an automated AI pipeline (DeepSeek). Sources: public RSS feeds. "
            "This document is for personal awareness only and is not investment advice. "
            f"© {data['date'][-4:]} {DEVELOPER}.",
            styles["disclaimer"],
        ),
    ]

    label = data.get("report_label", "Briefing")
    footer = _footer_factory(label, data["session"], data["date"])
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buf.seek(0)
    return buf