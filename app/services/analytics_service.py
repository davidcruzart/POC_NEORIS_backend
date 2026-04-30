import json
import logging
import os
import tempfile
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from markitdown import MarkItDown

from app.config import DEFAULT_MODEL_NAME
from app.prompts.analytics_prompts import (
    ANALYTICS_INSIGHTS_PROMPT,
    FINANCIAL_EXTRACTION_PROMPT,
)
from app.schemas.analytics import AnalyticsExtraction, AnalyticsInsights, FinancialMetric

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self):
        self.markitdown = MarkItDown()
        self.extraction_prompt = ChatPromptTemplate.from_template(FINANCIAL_EXTRACTION_PROMPT)
        self.insights_prompt = ChatPromptTemplate.from_template(ANALYTICS_INSIGHTS_PROMPT)

        self.extraction_llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        ).with_structured_output(AnalyticsExtraction)

        self.insights_llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        ).with_structured_output(AnalyticsInsights)

    def analyze(
        self,
        raw_text: str,
        document_type: str,
        file_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        warnings: list[str] = []

        content = self._extract_markdown(file_bytes, filename)

        if not self._is_valid_text(content):
            return self._empty_result(
                document_type=document_type,
                filename=filename,
                warnings=["No se pudo extraer contenido útil con MarkItDown."],
            )

        extraction = self._extract_metrics(content)
        rows = self._build_rows(extraction.metrics)

        if not rows:
            warnings.append("No se detectaron métricas financieras comparativas claras.")

        chart_specs = self._build_chart_specs(rows)

        return {
            "document_type": document_type,
            "rows": rows,
            "metrics": self._build_metrics_preview(rows),
            "percentages": self._build_percentages_preview(rows),
            "chart_specs": chart_specs,
            "insights": self._generate_insights(rows),
            "warnings": warnings,
            "metadata": {
                "method": "markitdown_llm_structured_analytics",
                "metrics_detected": len(rows),
                "charts_generated": len(chart_specs),
                "source_filename": filename,
            },
        }

    def _extract_markdown(self, file_bytes: bytes | None, filename: str | None) -> str:
        if not file_bytes:
            return ""

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._suffix(filename)) as file:
                file.write(file_bytes)
                temp_path = file.name

            result = self.markitdown.convert(temp_path)
            return str(getattr(result, "text_content", "") or "").strip()

        except Exception as exc:
            logger.warning("MarkItDown falló en analytics: %s", exc)
            return ""

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def _extract_metrics(self, content: str) -> AnalyticsExtraction:
        try:
            chain = self.extraction_prompt | self.extraction_llm
            return chain.invoke({"texto": content[:60_000]})

        except Exception as exc:
            logger.error("Error extrayendo métricas financieras: %s", exc)
            return AnalyticsExtraction()

    def _build_rows(self, metrics: list[FinancialMetric]) -> list[dict[str, Any]]:
        rows = []
        seen = set()

        for metric in metrics:
            label = self._clean(metric.label)
            if not label:
                continue

            value_1 = float(metric.value_current)
            value_2 = float(metric.value_previous)

            key = (label.lower(), value_1, value_2)
            if key in seen:
                continue

            seen.add(key)

            rows.append(
                {
                    "statement": metric.category or "other",
                    "section": metric.category or "other",
                    "label": label,
                    "period_1": metric.period_current or "Actual",
                    "value_1": value_1,
                    "period_2": metric.period_previous or "Anterior",
                    "value_2": value_2,
                    "unit": metric.unit or "",
                    "delta_abs": round(value_1 - value_2, 2),
                    "delta_pct": self._delta_pct(value_1, value_2),
                }
            )

        return rows

    def _generate_insights(self, rows: list[dict[str, Any]]) -> list[str]:
        if not rows:
            return []

        try:
            chain = self.insights_prompt | self.insights_llm
            result = chain.invoke(
                {
                    "datos": json.dumps(
                        rows[:30],
                        ensure_ascii=False,
                        indent=2,
                    )
                }
            )
            return [str(item).strip() for item in result.insights[:6] if str(item).strip()]

        except Exception as exc:
            logger.warning("Error generando insights financieros: %s", exc)
            return self._basic_insights(rows)

    @staticmethod
    def _build_metrics_preview(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "label": row["label"],
                "value": row["value_1"],
                "raw_value": str(row["value_1"]),
                "context": row.get("section"),
            }
            for row in rows[:30]
        ]

    @staticmethod
    def _build_percentages_preview(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "label": f"{row['label']} var",
                "value": row["delta_pct"],
                "raw_value": f"{row['delta_pct']}%",
                "context": f"{row['period_1']} vs {row['period_2']}",
            }
            for row in rows
            if row.get("delta_pct") is not None
        ][:30]

    @staticmethod
    def _build_chart_specs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []

        top = rows[:10]

        return [
            {
                "title": "Comparativa financiera",
                "chart_type": "bar",
                "reason": "Compara el periodo actual frente al periodo anterior.",
                "series": [
                    {
                        "name": "Actual",
                        "data": [{"x": row["label"], "y": row["value_1"]} for row in top],
                    },
                    {
                        "name": "Anterior",
                        "data": [{"x": row["label"], "y": row["value_2"]} for row in top],
                    },
                ],
            }
        ]

    @staticmethod
    def _basic_insights(rows: list[dict[str, Any]]) -> list[str]:
        ordered = sorted(
            [row for row in rows if row.get("delta_pct") is not None],
            key=lambda row: abs(row["delta_pct"]),
            reverse=True,
        )

        return [
            f"{row['label']} {'aumentó' if row['delta_pct'] > 0 else 'disminuyó'} "
            f"un {abs(row['delta_pct'])}% respecto al periodo anterior."
            for row in ordered[:3]
        ]

    @staticmethod
    def _is_valid_text(text: str | None) -> bool:
        clean = str(text or "").strip()
        return bool(clean) and clean.lower() not in {"none", "null", "nan"} and not clean.startswith("%PDF")

    @staticmethod
    def _clean(value: str | None) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _delta_pct(value_1: float, value_2: float) -> float | None:
        if value_2 == 0:
            return None

        return round(((value_1 - value_2) / abs(value_2)) * 100, 2)

    @staticmethod
    def _suffix(filename: str | None) -> str:
        if filename and "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()

        return ".txt"

    @staticmethod
    def _empty_result(
        document_type: str,
        filename: str | None,
        warnings: list[str],
    ) -> dict[str, Any]:
        return {
            "document_type": document_type,
            "rows": [],
            "metrics": [],
            "percentages": [],
            "chart_specs": [],
            "insights": [],
            "warnings": warnings,
            "metadata": {
                "method": "markitdown_llm_structured_analytics",
                "metrics_detected": 0,
                "charts_generated": 0,
                "source_filename": filename,
            },
        }