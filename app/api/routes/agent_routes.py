import traceback

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.dependencies import get_agent_service, get_ingestion_service
from app.core.constants import ALLOWED_INPUT_EXTENSIONS
from app.schemas.agent import AgentResponse
from app.services.agent_service import AgentService
from app.services.ingestion_service import IngestionService


router = APIRouter(tags=["agent"])


@router.post("/agent/execute", response_model=AgentResponse)
async def execute_agent_flow(
    file: UploadFile = File(...),
    percentage: int = Form(30),
    user_request: str = Form(default="Resume este documento"),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    filename = (file.filename or "").lower()

    if not filename.endswith(ALLOWED_INPUT_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Formato de archivo no permitido.")

    try:
        text = ingestion_service.extract_text(file)

        initial_state = {
            "raw_text": text,
            "user_request": user_request,
            "percentage": percentage,
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