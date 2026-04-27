from typing import Any

from pydantic import BaseModel, Field

from app.schemas.analytics import AnalyticsResult


class AgentSummaryPayload(BaseModel):
    summary: str
    summary_words: int
    original_words: int
    target_words: int
    was_capped: bool
    max_target_words: int


class AgentResponse(BaseModel):
    document_type: str
    user_intent: str
    status: str = "completed"

    summary_result: AgentSummaryPayload | None = None
    analytics_result: AnalyticsResult | None = None

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)