import json
import traceback
from functools import lru_cache
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.config import (
    ALLOWED_INPUT_EXTENSIONS,
    ALLOWED_OUTPUT_FORMATS,
    MEDIA_TYPES,
)
from app.implementations.exporters.docx_exporter import DocxExporter
from app.implementations.exporters.pdf_exporter import PdfExporter
from app.implementations.exporters.txt_exporter import TxtExporter
from app.implementations.file_readers.langchain_file_reader import LangchainFileReader
from app.implementations.summarizers.openai_summarizer import OpenAISummarizer
from app.schemas.agent import AgentResponse
from app.services.agent_service import AgentService
from app.services.export_service import ExportService
from app.services.ingestion_service import IngestionService
from app.services.summary_service import SummaryService

router = APIRouter()


@lru_cache
def get_file_reader():
    return LangchainFileReader()


@lru_cache
def get_summarizer():
    return OpenAISummarizer()


@lru_cache
def get_exporters():
    return {
        "txt": TxtExporter(),
        "pdf": PdfExporter(),
        "docx": DocxExporter(),
    }


@lru_cache
def get_ingestion_service():
    return IngestionService(file_reader=get_file_reader())


@lru_cache
def get_summary_service():
    return SummaryService(summarizer=get_summarizer())


@lru_cache
def get_export_service():
    return ExportService(exporters=get_exporters())


@lru_cache
def get_agent_service():
    return AgentService()


def validate_input_filename(filename: str | None, field_name: str = "archivo") -> str:
    normalized = (filename or "").lower()

    if not normalized.endswith(ALLOWED_INPUT_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Formato de {field_name} no permitido.",
        )

    return filename or "uploaded_file"


def parse_chat_history(chat_history: str | None) -> list:
    if not chat_history:
        return []

    try:
        parsed = json.loads(chat_history)

        if isinstance(parsed, list):
            return parsed

        return []

    except json.JSONDecodeError:
        return []


async def read_and_extract_file(
    file: UploadFile,
    ingestion_service: IngestionService,
    field_name: str = "archivo",
) -> tuple[bytes, str, str]:
    filename = validate_input_filename(file.filename, field_name=field_name)
    file_bytes = await file.read()

    text = ingestion_service.extract_text_from_bytes(
        file_bytes=file_bytes,
        filename=filename,
    )

    return file_bytes, text, filename


def build_agent_response(result: dict) -> AgentResponse:
    return AgentResponse(
        document_type=result.get("document_type", "generic"),
        user_intent=result.get("user_intent", "summarize"),
        status="completed",
        summary_result=result.get("summary_result"),
        analytics_result=result.get("analytics_result"),
        comparison_result=result.get("comparison_result"),
        qa_result=result.get("qa_result"),
        warnings=result.get("warnings", []),
        errors=result.get("errors", []),
        metadata=result.get("metadata", {}),
    )


@router.post("/export", tags=["export"])
async def export_summary(
    summary: str = Form(...),
    output_format: str = Form(...),
    export_service: ExportService = Depends(get_export_service),
):
    output_format = output_format.lower()

    if output_format not in ALLOWED_OUTPUT_FORMATS:
        raise HTTPException(status_code=400, detail="Formato de salida no soportado.")

    try:
        result = export_service.export_text(summary, output_format)

        return StreamingResponse(
            BytesIO(result["file_bytes"]),
            media_type=MEDIA_TYPES[result["output_format"]],
            headers={
                "Content-Disposition": f'attachment; filename="{result["filename"]}"'
            },
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Error interno al exportar el resumen.",
        ) from exc


@router.post("/agent/execute", response_model=AgentResponse, tags=["agent"])
async def execute_agent_flow(
    file: UploadFile = File(...),
    second_file: UploadFile | None = File(default=None),
    percentage: int = Form(30),
    user_request: str = Form(default="Resume este documento"),
    chat_history: str | None = Form(default=None),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    try:
        file_bytes, text, filename = await read_and_extract_file(
            file=file,
            ingestion_service=ingestion_service,
            field_name="archivo principal",
        )

        second_raw_text = None
        second_file_bytes = None
        second_filename = None

        if second_file is not None and second_file.filename:
            second_file_bytes, second_raw_text, second_filename = await read_and_extract_file(
                file=second_file,
                ingestion_service=ingestion_service,
                field_name="segundo archivo",
            )

        initial_state = {
            "raw_text": text,
            "file_bytes": file_bytes,
            "filename": filename,
            "second_raw_text": second_raw_text,
            "second_file_bytes": second_file_bytes,
            "second_filename": second_filename,
            "user_request": user_request,
            "percentage": percentage,
            "chat_history": parse_chat_history(chat_history),
            "warnings": [],
            "errors": [],
            "metadata": {},
        }

        result = agent_service.run_flow(initial_state)
        return build_agent_response(result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except HTTPException:
        raise

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno en el flujo agéntico: {exc}",
        ) from exc


@router.post("/qa/index", tags=["qa"])
async def index_qa_document(
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    try:
        file_bytes, text, filename = await read_and_extract_file(
            file=file,
            ingestion_service=ingestion_service,
            field_name="archivo QA",
        )

        initial_state = {
            "raw_text": text,
            "file_bytes": file_bytes,
            "filename": filename,
            "user_request": "Indexa este documento para QA.",
            "user_intent": "qa_index",
            "percentage": 0,
            "warnings": [],
            "errors": [],
            "metadata": {},
        }

        result = agent_service.run_flow(initial_state)
        qa_index_result = result.get("qa_index_result", {})

        if not qa_index_result.get("document_id"):
            raise HTTPException(
                status_code=400,
                detail=qa_index_result.get(
                    "message",
                    "No se pudo indexar el documento.",
                ),
            )

        return {
            **qa_index_result,
            "agent_metadata": result.get("metadata", {}),
            "warnings": result.get("warnings", []),
            "errors": result.get("errors", []),
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except HTTPException:
        raise

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno indexando documento QA: {exc}",
        ) from exc


@router.post("/qa/ask", tags=["qa"])
async def ask_qa_document(
    document_id: str = Form(...),
    question: str = Form(...),
    agent_service: AgentService = Depends(get_agent_service),
):
    try:
        initial_state = {
            "document_id": document_id,
            "user_request": question,
            "user_intent": "qa_ask",
            "percentage": 0,
            "warnings": [],
            "errors": [],
            "metadata": {},
        }

        result = agent_service.run_flow(initial_state)
        qa_result = result.get("qa_result", {})

        return {
            **qa_result,
            "agent_metadata": result.get("metadata", {}),
            "warnings": result.get("warnings", []),
            "errors": result.get("errors", []),
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno respondiendo QA: {exc}",
        ) from exc