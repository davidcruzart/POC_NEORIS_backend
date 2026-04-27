from app.implementations.exporters.docx_exporter import DocxExporter
from app.implementations.exporters.pdf_exporter import PdfExporter
from app.implementations.exporters.txt_exporter import TxtExporter
from app.implementations.file_readers.langchain_file_reader import LangchainFileReader
from app.implementations.summarizers.openai_summarizer import OpenAISummarizer
from app.services.agent_service import AgentService
from app.services.analytics_service import AnalyticsService
from app.services.classification_service import ClassificationService
from app.services.export_service import ExportService
from app.services.ingestion_service import IngestionService
from app.services.summary_service import SummaryService


def get_file_reader():
    return LangchainFileReader()


def get_summarizer():
    return OpenAISummarizer()


def get_exporters():
    return {
        "txt": TxtExporter(),
        "pdf": PdfExporter(),
        "docx": DocxExporter(),
    }


def get_ingestion_service():
    return IngestionService(file_reader=get_file_reader())


def get_summary_service():
    return SummaryService(summarizer=get_summarizer())


def get_export_service():
    return ExportService(exporters=get_exporters())


def get_classification_service():
    return ClassificationService()


def get_analytics_service():
    return AnalyticsService()


def get_agent_service():
    return AgentService()