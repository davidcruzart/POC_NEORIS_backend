from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.dependencies import get_ingestion_service, get_summary_service
from app.core.constants import ALLOWED_INPUT_EXTENSIONS
from app.schemas.summary import SummaryResponse
from app.services.ingestion_service import IngestionService
from app.services.summary_service import SummaryService


router = APIRouter(tags=["summary"])


@router.post("/summary", response_model=SummaryResponse)
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