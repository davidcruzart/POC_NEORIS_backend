from typing import Any

from pydantic import BaseModel, Field


class AnalyticsMetric(BaseModel):
    label: str
    value: float
    raw_value: str
    context: str | None = None


class FinancialRow(BaseModel):
    statement: str
    section: str
    label: str

    period_1: str | None = None
    value_1: float

    period_2: str | None = None
    value_2: float

    unit: str | None = None

    delta_abs: float | None = None
    delta_pct: float | None = None


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

    rows: list[FinancialRow] = Field(default_factory=list)
    metrics: list[AnalyticsMetric] = Field(default_factory=list)
    percentages: list[AnalyticsMetric] = Field(default_factory=list)

    chart_specs: list[ChartSpec] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)