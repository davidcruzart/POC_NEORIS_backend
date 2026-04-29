from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.interfaces.exporter import Exporter


class PdfExporter(Exporter):
    def export(self, text: str) -> bytes:
        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title="Resumen generado",
            author="Agentic Document Processor",
            subject="Resumen exportado",
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="CustomTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_LEFT,
            spaceAfter=18,
        )

        body_style = ParagraphStyle(
            name="CustomBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=8,
        )

        story = [
            Paragraph("Resumen generado", title_style),
            Spacer(1, 0.3 * cm),
        ]

        clean_text = self._sanitize_text(text)

        for paragraph in clean_text.split("\n"):
            paragraph = paragraph.strip()

            if not paragraph:
                story.append(Spacer(1, 0.25 * cm))
                continue

            story.append(
                Paragraph(
                    escape(paragraph),
                    body_style,
                )
            )

        document.build(story)

        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _sanitize_text(text: str) -> str:
        if not text:
            return ""

        return (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\t", " ")
            .strip()
        )