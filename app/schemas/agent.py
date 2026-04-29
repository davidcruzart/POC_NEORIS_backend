from typing import Any

from pydantic import BaseModel, Field

from app.schemas.analytics import AnalyticsResult
from app.schemas.summary import SummaryResponse


class ComparisonResult(BaseModel):
    document_a_summary: str | None = None
    document_b_summary: str | None = None
    document_a_keywords: list[str] = Field(default_factory=list)
    document_b_keywords: list[str] = Field(default_factory=list)
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    comparison_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QAResult(BaseModel):
    question: str
    answer: str
    retrieved_chunks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    document_type: str
    user_intent: str
    status: str = "completed"

    summary_result: SummaryResponse | None = None
    analytics_result: AnalyticsResult | None = None
    comparison_result: ComparisonResult | None = None
    qa_result: QAResult | None = None

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)