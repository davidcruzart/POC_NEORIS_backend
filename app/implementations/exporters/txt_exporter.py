from app.interfaces.exporter import Exporter


class TxtExporter(Exporter):
    def export(self, text: str) -> bytes:
        return text.encode("utf-8")