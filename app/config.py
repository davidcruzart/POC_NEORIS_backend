import logging
import os

from dotenv import load_dotenv

load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_MODEL_NAME = "gpt-5-mini"
DEFAULT_MODEL_TEMPERATURE = 0.2

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_TEXT_LENGTH_CHARS = 1_500_000
MAX_FRAGMENTS = 80
MAX_TARGET_WORDS = 5000

MIN_SUMMARY_PERCENTAGE = 10
MAX_SUMMARY_PERCENTAGE = 80

CHUNK_SIZE = 8000
CHUNK_OVERLAP = 500
LARGE_DOCUMENT_BATCH_SIZE = 4
MAX_SUMMARY_WORKERS = 4

ALLOWED_INPUT_EXTENSIONS = (".pdf", ".txt", ".docx", ".csv")

ALLOWED_OUTPUT_FORMATS = ("txt", "pdf", "docx")

MEDIA_TYPES = {
    "txt": "text/plain",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

DOCUMENT_TYPES = (
    "novel",
    "academic",
    "business_report",
    "project_documentation",
    "generic",
)

USER_INTENTS = (
    "summarize",
    "extract_analytics",
    "compare_documents",
    "qa_rag",
)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
