from app.interfaces.file_reader import FileReader


class IngestionService:
    def __init__(self, file_reader: FileReader):
        self.file_reader = file_reader

    def extract_text(self, uploaded_file) -> str:
        return self.file_reader.read(uploaded_file)

    def extract_text_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        return self.file_reader.read_from_bytes(
            file_bytes=file_bytes,
            filename=filename,
        )