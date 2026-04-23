from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.interfaces.exporter import Exporter


class PdfExporter(Exporter):
    def export(self, text: str) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        width, height = A4
        x = 50
        y = height - 50
        max_width = width - 100

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(x, y, "Resumen generado")
        y -= 30

        pdf.setFont("Helvetica", 11)

        for line in text.split("\n"):
            if not line.strip():
                y -= 10
                continue

            words = line.split()
            current_line = ""

            for word in words:
                candidate = f"{current_line} {word}".strip()

                if pdf.stringWidth(candidate, "Helvetica", 11) < max_width:
                    current_line = candidate
                else:
                    pdf.drawString(x, y, current_line)
                    y -= 18
                    current_line = word

                    if y < 50:
                        pdf.showPage()
                        pdf.setFont("Helvetica", 11)
                        y = height - 50

            if current_line:
                pdf.drawString(x, y, current_line)
                y -= 18

                if y < 50:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 11)
                    y = height - 50

            y -= 8

        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()