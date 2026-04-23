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
    "qa",
    "extract_actions",
    "extract_risks",
    "extract_keywords",
    "generate_questions",
    "compare_documents",
    "extract_analytics",
)