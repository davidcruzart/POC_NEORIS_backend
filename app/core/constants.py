ALLOWED_INPUT_EXTENSIONS = (".pdf", ".txt", ".docx")

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