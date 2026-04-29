from fastapi import FastAPI

from app.api import router as api_router
from app.config import configure_logging


configure_logging()

app = FastAPI(title="Document Summarizer API")

app.include_router(api_router, prefix="/api")
