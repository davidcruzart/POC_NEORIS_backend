from typing import Any

from pydantic import BaseModel, Field


class ComparisonExtraction(BaseModel):
    document_a_summary: str | None = None
    document_b_summary: str | None = None

    document_a_keywords: list[str] = Field(default_factory=list)
    document_b_keywords: list[str] = Field(default_factory=list)

    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)

    document_a_advantages: list[str] = Field(default_factory=list)
    document_a_disadvantages: list[str] = Field(default_factory=list)
    document_b_advantages: list[str] = Field(default_factory=list)
    document_b_disadvantages: list[str] = Field(default_factory=list)

    comparison_summary: str | None = None


class ComparisonResult(BaseModel):
    document_a_summary: str | None = None
    document_b_summary: str | None = None

    document_a_keywords: list[str] = Field(default_factory=list)
    document_b_keywords: list[str] = Field(default_factory=list)

    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)

    document_a_advantages: list[str] = Field(default_factory=list)
    document_a_disadvantages: list[str] = Field(default_factory=list)
    document_b_advantages: list[str] = Field(default_factory=list)
    document_b_disadvantages: list[str] = Field(default_factory=list)

    comparison_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)