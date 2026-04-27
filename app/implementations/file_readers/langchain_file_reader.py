import os
import tempfile

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)

from app.core.config import MAX_FILE_SIZE_BYTES
from app.core.exceptions import (
    EmptyExtractedTextError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.interfaces.file_reader import FileReader


class LangchainFileReader(FileReader):
    def read(self, uploaded_file) -> str:
        filename = uploaded_file.filename or "uploaded_file"
        file_bytes = uploaded_file.file.read()

        return self.read_from_bytes(
            file_bytes=file_bytes,
            filename=filename,
        )

    def read_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        file_name = (filename or "").lower()

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"El archivo es demasiado grande. Tamaño máximo permitido: "
                f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
            )

        if file_name.endswith(".pdf"):
            suffix = ".pdf"
            loader_class = PyMuPDFLoader
        elif file_name.endswith(".txt"):
            suffix = ".txt"
            loader_class = TextLoader
        elif file_name.endswith(".docx"):
            suffix = ".docx"
            loader_class = Docx2txtLoader
        else:
            raise UnsupportedFileTypeError(
                "Archivo no soportado. Solo se admiten PDF, TXT y DOCX."
            )

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name

            if suffix == ".txt":
                loader = loader_class(temp_path, encoding="utf-8")
            else:
                loader = loader_class(temp_path)

            documents = loader.load()
            extracted_text = "\n".join(doc.page_content for doc in documents).strip()

            if not extracted_text:
                raise EmptyExtractedTextError("El texto extraído está vacío.")

            return extracted_text

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)