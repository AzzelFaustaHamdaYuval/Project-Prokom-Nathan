"""
detector/pdf_report.py
Generate a downloadable PDF study session report using ReportLab.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


# Brand colours
PINK_PRIMARY = colors.HexColor("#FF6FAE")
PINK_SOFT    = colors.HexColor("#FFD6E7")
PINK_LIGHT   = colors.HexColor("#FFF0F7")
DARK_TEXT    = colors.HexColor("#333333")
GREY_TEXT    = colors.HexColor("#888888")


def _fmt_time(seconds: int) -> str:
    h  = seconds // 3600
    m  = (seconds % 3600) // 60
    s  = seconds % 60
    if h:
        return f"{h}j {m}m {s}d"
    return f"{m}m {s}d"


def generate_pdf_report(session: dict, suggestions: list[str]) -> bytes:
    """
    Generate a PDF byte stream for a given session dict.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Title ──────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title", fontSize=24, textColor=PINK_PRIMARY,
        alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "Sub", fontSize=11, textColor=GREY_TEXT,
        alignment=TA_CENTER, spaceAfter=16
    )

    story.append(Paragraph("📚 StudyFocus AI", title_style))
    story.append(Paragraph("Laporan Sesi Belajar", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PINK_PRIMARY))
    story.append(Spacer(1, 0.4*cm))

    # ── Meta ───────────────────────────────────────────────────────────────
    label_style = ParagraphStyle("Label", fontSize=10, textColor=GREY_TEXT)
    value_style = ParagraphStyle("Value", fontSize=12, textColor=DARK_TEXT, fontName="Helvetica-Bold")

    story.append(Paragraph(f"Tanggal: {session.get('date', '-')}", label_style))
    story.append(Spacer(1, 0.3*cm))

    # ── Score banner ───────────────────────────────────────────────────────
    score = session.get("focus_score", 0)
    category = session.get("productivity_category", "Poor")

    score_data = [[
        Paragraph(f"<font size='36' color='#{PINK_PRIMARY.hexval()[2:]}'><b>{score}%</b></font>", styles["Normal"]),
        Paragraph(f"<font size='18'><b>{category}</b></font><br/><font size='10' color='#888888'>Focus Score</font>", styles["Normal"]),
    ]]
    score_table = Table(score_data, colWidths=[6*cm, 10*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PINK_LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PINK_LIGHT]),
        ("BOX",  (0, 0), (-1, -1), 1, PINK_SOFT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Stats table ────────────────────────────────────────────────────────
    stats_data = [
        ["Metrik", "Nilai"],
        ["⏱ Total Waktu Belajar",   _fmt_time(session.get("study_duration", 0))],
        ["😴 Durasi Mengantuk",       _fmt_time(session.get("sleepy_duration", 0))],
        ["🧍 Postur Buruk",           _fmt_time(session.get("poor_posture_duration", 0))],
        ["👀 Durasi Distraksi",       _fmt_time(session.get("distraction_duration", 0))],
        ["⚠️ Jumlah Peringatan",     str(session.get("warning_count", 0))],
    ]
    stat_table = Table(stats_data, colWidths=[10*cm, 6*cm])
    stat_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), PINK_PRIMARY),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 11),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, PINK_LIGHT]),
        ("FONTSIZE",     (0, 1), (-1, -1), 10),
        ("GRID",         (0, 0), (-1, -1), 0.5, PINK_SOFT),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    story.append(stat_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Suggestions ────────────────────────────────────────────────────────
    section_style = ParagraphStyle(
        "Section", fontSize=13, textColor=PINK_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=6
    )
    body_style = ParagraphStyle("Body", fontSize=10, textColor=DARK_TEXT, leading=16)

    story.append(Paragraph("💡 Rekomendasi AI Study Coach", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PINK_SOFT))
    story.append(Spacer(1, 0.2*cm))

    for i, suggestion in enumerate(suggestions, 1):
        story.append(Paragraph(f"{i}. {suggestion}", body_style))
        story.append(Spacer(1, 0.2*cm))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=PINK_SOFT))
    footer_style = ParagraphStyle("Footer", fontSize=8, textColor=GREY_TEXT, alignment=TA_CENTER)
    story.append(Paragraph("StudyFocus AI • Dibuat dengan ❤ untuk produktivitas mahasiswa", footer_style))

    doc.build(story)
    return buffer.getvalue()