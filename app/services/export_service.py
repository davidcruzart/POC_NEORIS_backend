from app.exceptions import UnsupportedOutputFormatError


class ExportService:
    def __init__(self, exporters: dict):
        self.exporters = exporters

    def export_text(self, text: str, output_format: str) -> dict:
        normalized_format = output_format.lower()

        if normalized_format not in self.exporters:
            raise UnsupportedOutputFormatError(
                "Formato de salida no soportado. Usa txt, pdf o docx."
            )

        file_bytes = self.exporters[normalized_format].export(text)
        filename = f"resumen.{normalized_format}"

        return {
            "file_bytes": file_bytes,
            "filename": filename,
            "output_format": normalized_format,
        }