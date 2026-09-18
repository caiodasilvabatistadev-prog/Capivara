from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.dashboard import Dashboard


def make_pdf(data: Dashboard) -> bytes:
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "BodyReport",
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            spaceAfter=5,
            alignment=TA_LEFT,
        )
    )
    styles.add(ParagraphStyle("SmallReport", parent=styles["BodyReport"], fontSize=8, leading=11))
    styles["Title"].textColor = colors.HexColor("#123d34")
    styles["Heading1"].textColor = colors.HexColor("#123d34")
    styles["Heading1"].fontSize = 16
    styles["Heading1"].spaceBefore = 14
    styles["Heading2"].fontSize = 11
    styles["Heading1"].keepWithNext = True
    styles["Heading2"].keepWithNext = True
    story: list[Any] = []

    def paragraph(value: str, style: str = "BodyReport") -> Paragraph:
        return Paragraph(escape(value).replace("→", "-").replace("–", "-"), styles[style])

    story.extend(
        [
            paragraph("PUXANDO A CAPIVARA | CONSULTA PÚBLICA", "SmallReport"),
            paragraph(data.politician.name, "Title"),
            paragraph(f"{data.politician.role} | {data.politician.institution}"),
            paragraph(
                f"Período da fonte: {data.year or 'não informado'} | "
                f"Consulta: {data.fetched_at.strftime('%d/%m/%Y %H:%M UTC')}",
                "SmallReport",
            ),
            paragraph("Perfil e indicadores disponíveis", "Heading1"),
        ]
    )
    for metric in data.metrics:
        story.append(paragraph(f"{metric.label}: {metric.value}"))
    story.extend(
        [
            Spacer(1, 4 * mm),
            paragraph(data.notice, "SmallReport"),
            paragraph(
                "Os percentuais nas tabelas são reproduzidos como publicados. "
                "A fonte pode apresentar percentuais negativos ou superiores a 100%; "
                "não os utilizamos para avaliar o mandato.",
                "SmallReport",
            ),
            PageBreak(),
        ]
    )
    for section in data.sections:
        story.append(paragraph(section.title, "Heading1"))
        for block in section.blocks:
            if block.kind == "table":
                caption = paragraph(block.text, "Heading2")
                count = max(len(row) for row in block.rows)
                rows = [[paragraph(cell, "SmallReport") for cell in row] for row in block.rows]
                table = Table(
                    rows, colWidths=[174 * mm / count] * count, repeatRows=1, hAlign="LEFT"
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4f0eb")),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#f5f7f6")],
                            ),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.extend([KeepTogether([caption, table]), Spacer(1, 4 * mm)])
            else:
                story.append(
                    paragraph(block.text, "Heading2" if block.kind == "heading" else "BodyReport")
                )
    story.extend(
        [
            paragraph("Fonte e limites do relatório", "Heading1"),
            paragraph(data.politician.source_url, "SmallReport"),
            paragraph(
                "Relatório dos dados presentes na dashboard e nas fontes indicadas em suas seções. "
                "Não inclui o conteúdo de páginas vinculadas, vídeos ou áudios. "
                "Emendas autorizadas, empenhadas e pagas são etapas diferentes; "
                "esses valores não devem ser somados.",
                "SmallReport",
            ),
        ]
    )

    def footer(canvas: Canvas, doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#cbd9d3"))
        canvas.line(18 * mm, 16 * mm, 192 * mm, 16 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(18 * mm, 11 * mm, "Puxando a Capivara | Dados de fontes oficiais")
        canvas.drawRightString(192 * mm, 11 * mm, f"Página {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"Perfil público - {data.politician.name}",
        author="Puxando a Capivara - Consulta Pública",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
