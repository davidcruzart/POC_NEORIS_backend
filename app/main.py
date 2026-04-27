from fastapi import FastAPI

from app.api.routes.summary_routes import router as summary_router
from app.api.routes.export_routes import router as export_router
from app.api.routes.agent_routes import router as agent_router
from app.core.logging import configure_logging


configure_logging()

app = FastAPI(title="Document Summarizer API")

app.include_router(summary_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(agent_router, prefix="/api")