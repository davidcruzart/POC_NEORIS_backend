import json
import traceback
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
from app.schemas.summary import SummaryResponse
from app.services.agent_service import AgentService
from app.services.export_service import ExportService
from app.services.ingestion_service import IngestionService
from app.services.summary_service import SummaryService


router = APIRouter()


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


def get_agent_service():
    return AgentService()


@router.post("/summary", response_model=SummaryResponse, tags=["summary"])
async def summarize_document(
    file: UploadFile = File(...),
    percentage: int = Form(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    summary_service: SummaryService = Depends(get_summary_service),
):
    filename = (file.filename or "").lower()

    if not filename.endswith(ALLOWED_INPUT_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Formato de archivo no permitido.")

    try:
        text = ingestion_service.extract_text(file)
        result = summary_service.summarize_text(text=text, percentage=percentage)
        return SummaryResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Error interno al resumir el documento.",
        ) from exc


@router.post("/export", tags=["export"])
async def export_summary(
    summary: str = Form(...),
    output_format: str = Form(...),
    export_service: ExportService = Depends(get_export_service),
):
    if output_format.lower() not in ALLOWED_OUTPUT_FORMATS:
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
    filename = (file.filename or "").lower()

    if not filename.endswith(ALLOWED_INPUT_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Formato de archivo no permitido.")

    try:
        parsed_chat_history = []

        if chat_history:
            try:
                parsed_chat_history = json.loads(chat_history)

                if not isinstance(parsed_chat_history, list):
                    parsed_chat_history = []

            except json.JSONDecodeError:
                parsed_chat_history = []

        file_bytes = await file.read()
        text = ingestion_service.extract_text_from_bytes(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded_file",
        )

        second_raw_text = None
        second_file_bytes = None
        second_filename = None

        if second_file is not None and second_file.filename:
            second_filename_value = (second_file.filename or "").lower()

            if not second_filename_value.endswith(ALLOWED_INPUT_EXTENSIONS):
                raise HTTPException(
                    status_code=400,
                    detail="Formato del segundo archivo no permitido.",
                )

            second_file_bytes = await second_file.read()
            second_raw_text = ingestion_service.extract_text_from_bytes(
                file_bytes=second_file_bytes,
                filename=second_file.filename or "second_uploaded_file",
            )
            second_filename = second_file.filename

        initial_state = {
            "raw_text": text,
            "file_bytes": file_bytes,
            "filename": file.filename,
            "second_raw_text": second_raw_text,
            "second_file_bytes": second_file_bytes,
            "second_filename": second_filename,
            "user_request": user_request,
            "percentage": percentage,
            "chat_history": parsed_chat_history,
            "warnings": [],
            "errors": [],
            "metadata": {},
        }

        result = agent_service.run_flow(initial_state)

        return AgentResponse(
            document_type=result["document_type"],
            user_intent=result["user_intent"],
            status="completed",
            summary_result=result.get("summary_result"),
            analytics_result=result.get("analytics_result"),
            comparison_result=result.get("comparison_result"),
            qa_result=result.get("qa_result"),
            warnings=result.get("warnings", []),
            errors=result.get("errors", []),
            metadata=result.get("metadata", {}),
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno en el flujo agéntico: {exc}",
        ) from exc
