from io import BytesIO

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_export_service
from app.core.constants import ALLOWED_OUTPUT_FORMATS, MEDIA_TYPES
from app.services.export_service import ExportService


router = APIRouter(tags=["export"])


@router.post("/export")
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