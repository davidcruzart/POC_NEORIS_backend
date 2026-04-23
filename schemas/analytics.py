from typing import Any

from pydantic import BaseModel, Field


class AnalyticsMetric(BaseModel):
    label: str
    value: float
    raw_value: str
    context: str | None = None


class ChartPoint(BaseModel):
    x: str
    y: float


class ChartSeries(BaseModel):
    name: str
    data: list[ChartPoint] = Field(default_factory=list)


class ChartSpec(BaseModel):
    chart_type: str
    title: str
    x_label: str
    y_label: str
    series: list[ChartSeries] = Field(default_factory=list)
    reason: str | None = None


class AnalyticsResult(BaseModel):
    document_type: str
    metrics: list[AnalyticsMetric] = Field(default_factory=list)
    percentages: list[AnalyticsMetric] = Field(default_factory=list)
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)