import logging
from typing import List, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from markitdown import MarkItDown
from pydantic import BaseModel, Field

from app.core.config import DEFAULT_MODEL_NAME
from app.prompts.analytics_prompts import FINANCIAL_EXTRACTION_PROMPT
from app.schemas.analytics import ChartPoint, ChartSeries, ChartSpec, FinancialRow

logger = logging.getLogger(__name__)


class FinancialTable(BaseModel):
    rows: List[FinancialRow] = Field(default_factory=list)


class AnalyticsService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        ).with_structured_output(FinancialTable)

        self.prompt = ChatPromptTemplate.from_template(FINANCIAL_EXTRACTION_PROMPT)

    def analyze(
        self,
        raw_text: str,
        document_type: str,
        file_bytes: bytes | None = None,
    ) -> dict:
        context = self._get_structured_context(raw_text, file_bytes)
        unit_multiplier = self._detect_unit_multiplier(context)

        filtered_context = self._filter_relevant_sections(context)

        raw_rows = self._extract_semantic_rows(filtered_context)

        if not raw_rows and filtered_context != context:
            logger.warning(
                "No se extrajeron filas desde el contexto filtrado. "
                "Reintentando con contexto completo recortado."
            )
            raw_rows = self._extract_semantic_rows(context[:50_000])

        clean_rows = self._validate_and_clean_rows(
            rows=raw_rows,
            unit_multiplier=unit_multiplier,
        )

        prioritized_rows = self._prioritize_rows(clean_rows)

        chart_specs = self._build_chart_specs(prioritized_rows)
        insights = self._generate_insights(prioritized_rows)

        return {
            "document_type": document_type,
            "rows": prioritized_rows,
            "metrics": self._build_metrics_preview(prioritized_rows),
            "percentages": self._build_percentages_preview(prioritized_rows),
            "chart_specs": chart_specs,
            "insights": insights,
            "warnings": self._generate_warnings(raw_rows, prioritized_rows),
            "metadata": {
                "raw_count": len(raw_rows),
                "validated_count": len(prioritized_rows),
                "chart_specs_generated": len(chart_specs),
                "insights_generated": len(insights),
                "unit_multiplier": unit_multiplier,
                "method": "hybrid_markitdown_llm_semantic_windows",
            },
        }

    def _get_structured_context(self, text: str, file_bytes: bytes | None) -> str:
        if file_bytes:
            try:
                md = MarkItDown()
                result = md.convert_binary(file_bytes)

                if result and result.text_content:
                    return result.text_content

            except Exception as exc:
                logger.warning("Fallo en MarkItDown, usando texto plano: %s", exc)

        return text

    @staticmethod
    def _detect_unit_multiplier(text: str) -> int:
        lowered = text.lower()

        if "in millions" in lowered or "in millions," in lowered:
            return 1_000_000

        if "in thousands" in lowered or "in thousands," in lowered:
            return 1_000

        if "en millones" in lowered:
            return 1_000_000

        if "en miles" in lowered:
            return 1_000

        return 1

    def _filter_relevant_sections(self, text: str) -> str:
        headers = [
            "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS",
            "CONDENSED CONSOLIDATED BALANCE SHEETS",
            "CONDENSED CONSOLIDATED STATEMENTS OF CASH FLOWS",
            "CONDENSED CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME",
            "CONDENSED CONSOLIDATED STATEMENTS OF SHAREHOLDERS’ EQUITY",
            "CONDENSED CONSOLIDATED STATEMENTS OF SHAREHOLDERS' EQUITY",
            "Note 2",
            "Note 3",
            "Note 4",
            "Note 5",
            "Note 10",
            "Revenue",
            "Segment Information",
            "Products and Services Performance",
            "Segment Operating Performance",
            "Gross Margin",
            "Operating Expenses",
            "Provision for Income Taxes",
            "Liquidity and Capital Resources",
        ]

        lines = text.splitlines()
        selected_content: list[str] = []
        used_ranges: list[tuple[int, int]] = []

        window_size = 120

        for header in headers:
            normalized_header = self._normalize_header(header)

            for index, line in enumerate(lines):
                normalized_line = self._normalize_header(line)

                if normalized_header in normalized_line:
                    start = index
                    end = min(index + window_size, len(lines))

                    if self._range_already_used(start, end, used_ranges):
                        continue

                    selected_content.extend(lines[start:end])
                    selected_content.append("\n")
                    used_ranges.append((start, end))
                    break

        if selected_content:
            return "\n".join(selected_content)[:50_000]

        fallback_lines = [
            line
            for line in lines
            if self._line_looks_financial(line)
        ]

        if fallback_lines:
            return "\n".join(fallback_lines[:4_000])[:50_000]

        return text[:50_000]

    @staticmethod
    def _normalize_header(value: str) -> str:
        normalized = value.upper()
        normalized = normalized.replace("—", "-")
        normalized = normalized.replace("–", "-")
        normalized = normalized.replace("’", "'")
        normalized = " ".join(normalized.split())
        return normalized

    @staticmethod
    def _range_already_used(
        start: int,
        end: int,
        used_ranges: list[tuple[int, int]],
    ) -> bool:
        for used_start, used_end in used_ranges:
            overlaps = start < used_end and end > used_start
            if overlaps:
                return True

        return False

    @staticmethod
    def _line_looks_financial(line: str) -> bool:
        lowered = line.lower()

        keywords = [
            "revenue",
            "net sales",
            "sales",
            "income",
            "gross margin",
            "operating income",
            "net income",
            "assets",
            "liabilities",
            "equity",
            "cash flow",
            "operating activities",
            "investing activities",
            "financing activities",
            "products",
            "services",
            "iphone",
            "mac",
            "ipad",
            "wearables",
            "americas",
            "europe",
            "greater china",
            "china",
            "japan",
            "asia pacific",
            "total",
            "cost of sales",
            "expenses",
            "research and development",
            "selling",
            "general and administrative",
        ]

        return any(keyword in lowered for keyword in keywords) or any(
            character.isdigit() for character in line
        )

    def _extract_semantic_rows(self, context: str) -> List[dict]:
        if not context or not context.strip():
            return []

        try:
            chain = self.prompt | self.llm
            result = chain.invoke({"texto": context[:50_000]})
            return [row.model_dump() for row in result.rows]

        except Exception as exc:
            logger.error("Error en extracción LLM de analytics: %s", exc)
            return []

    def _validate_and_clean_rows(
        self,
        rows: List[dict],
        unit_multiplier: int,
    ) -> List[dict]:
        clean_rows = []
        seen: set[Tuple[str, float, float]] = set()

        for row in rows:
            label = str(row.get("label", "")).strip()
            value_1 = row.get("value_1")
            value_2 = row.get("value_2")

            if not label or len(label) < 3:
                continue

            if self._is_noise_label(label):
                continue

            if not isinstance(value_1, (int, float)) or not isinstance(value_2, (int, float)):
                continue

            value_1 = float(value_1)
            value_2 = float(value_2)

            if abs(value_1) > 1_000_000_000_000 or abs(value_2) > 1_000_000_000_000:
                continue

            normalized_label = self._normalize_label(label)

            key = (normalized_label.lower(), value_1, value_2)
            if key in seen:
                continue

            seen.add(key)

            normalized_value_1 = value_1 * unit_multiplier
            normalized_value_2 = value_2 * unit_multiplier

            cleaned_row = {
                **row,
                "label": normalized_label,
                "value_1": normalized_value_1,
                "value_2": normalized_value_2,
                "raw_value_1": value_1,
                "raw_value_2": value_2,
                "unit_multiplier": unit_multiplier,
                "delta_abs": round(normalized_value_1 - normalized_value_2, 2),
                "delta_pct": self._calculate_delta_pct(
                    normalized_value_1,
                    normalized_value_2,
                ),
            }

            clean_rows.append(cleaned_row)

        return clean_rows

    def _prioritize_rows(self, rows: List[dict]) -> List[dict]:
        priority_map = {
            "total net sales": 1,
            "net sales": 2,
            "revenue": 3,
            "gross margin": 4,
            "operating income": 5,
            "net income": 6,
            "income before provision for income taxes": 7,
            "products": 8,
            "services": 9,
            "iphone": 10,
            "mac": 11,
            "ipad": 12,
            "wearables, home and accessories": 13,
            "americas": 14,
            "europe": 15,
            "greater china": 16,
            "japan": 17,
            "rest of asia pacific": 18,
            "cash and cash equivalents": 19,
            "total current assets": 20,
            "total non-current assets": 21,
            "total assets": 22,
            "accounts payable": 23,
            "total current liabilities": 24,
            "total non-current liabilities": 25,
            "total liabilities": 26,
            "total shareholders’ equity": 27,
            "total shareholders' equity": 27,
            "total liabilities and shareholders’ equity": 28,
            "total liabilities and shareholders' equity": 28,
            "cash generated by operating activities": 29,
            "cash generated by/(used in) investing activities": 30,
            "cash used in financing activities": 31,
        }

        def priority(row: dict) -> tuple[int, float]:
            normalized_label = self._normalize_priority_key(row.get("label", ""))
            return (
                priority_map.get(normalized_label, 999),
                -abs(float(row.get("value_1", 0))),
            )

        return sorted(rows, key=priority)

    @staticmethod
    def _normalize_priority_key(label: str) -> str:
        normalized = label.lower().strip()
        normalized = normalized.replace("’", "'")
        normalized = " ".join(normalized.split())
        return normalized

    @staticmethod
    def _normalize_label(label: str) -> str:
        return " ".join(label.strip().split())

    @staticmethod
    def _calculate_delta_pct(value_1: float, value_2: float) -> float | None:
        if value_2 == 0:
            return None

        return round(((value_1 - value_2) / value_2) * 100, 2)

    @staticmethod
    def _is_noise_label(label: str) -> bool:
        lowered = label.lower()

        noise_patterns = [
            "date:",
            "signature",
            "certification",
            "pursuant",
            "registrant",
            "commission",
            "form 10-q",
            "nasdaq",
            "trading symbol",
            "par value",
            "authorized",
            "issued and outstanding",
            "telephone number",
            "exact name",
            "address",
            "zip code",
            "page",
            "exhibit",
            "table of contents",
            "transition report",
            "common stock",
            "securities registered",
            "washington, d.c.",
            "for the quarterly period",
            "for the transition period",
            "large accelerated filer",
            "accelerated filer",
            "non-accelerated filer",
            "smaller reporting company",
            "emerging growth company",
        ]

        return any(pattern in lowered for pattern in noise_patterns)

    @staticmethod
    def _build_metrics_preview(rows: List[dict]) -> List[dict]:
        return [
            {
                "label": row["label"],
                "value": row["value_1"],
                "raw_value": str(row["raw_value_1"]),
                "context": row.get("statement") or row.get("section") or "Métrica financiera",
            }
            for row in rows[:30]
        ]

    @staticmethod
    def _build_percentages_preview(rows: List[dict]) -> List[dict]:
        percentages = []

        for row in rows:
            delta_pct = row.get("delta_pct")

            if delta_pct is None:
                continue

            percentages.append(
                {
                    "label": f"{row['label']} variation",
                    "value": delta_pct,
                    "raw_value": f"{delta_pct}%",
                    "context": "Periodo actual vs periodo anterior",
                }
            )

        return percentages[:30]

    def _build_chart_specs(self, rows: List[dict]) -> List[dict]:
        if len(rows) < 2:
            return []

        chart_specs = []

        main_chart = self._build_two_period_chart(
            rows=rows[:10],
            title="Métricas financieras clave",
            x_label="Métrica",
            y_label="Valor normalizado",
            reason="Comparación entre el periodo actual y el periodo anterior para las métricas financieras principales extraídas.",
        )

        if main_chart:
            chart_specs.append(main_chart)

        variation_chart = self._build_variation_chart(rows)

        if variation_chart:
            chart_specs.append(variation_chart)

        return chart_specs

    @staticmethod
    def _build_two_period_chart(
        rows: List[dict],
        title: str,
        x_label: str,
        y_label: str,
        reason: str,
    ) -> dict | None:
        if len(rows) < 2:
            return None

        return ChartSpec(
            chart_type="bar",
            title=title,
            x_label=x_label,
            y_label=y_label,
            series=[
                ChartSeries(
                    name="Periodo actual",
                    data=[
                        ChartPoint(x=row["label"], y=row["value_1"])
                        for row in rows
                    ],
                ),
                ChartSeries(
                    name="Periodo anterior",
                    data=[
                        ChartPoint(x=row["label"], y=row["value_2"])
                        for row in rows
                    ],
                ),
            ],
            reason=reason,
        ).model_dump()

    @staticmethod
    def _build_variation_chart(rows: List[dict]) -> dict | None:
        variation_rows = [
            row for row in rows
            if row.get("delta_pct") is not None
        ][:10]

        if len(variation_rows) < 2:
            return None

        return ChartSpec(
            chart_type="bar",
            title="Variación porcentual",
            x_label="Métrica",
            y_label="Variación (%)",
            series=[
                ChartSeries(
                    name="Variación %",
                    data=[
                        ChartPoint(x=row["label"], y=row["delta_pct"])
                        for row in variation_rows
                    ],
                )
            ],
            reason="Muestra el cambio porcentual entre los dos periodos comparados.",
        ).model_dump()

    @staticmethod
    def _generate_insights(rows: List[dict]) -> List[str]:
        insights = []

        sorted_rows = sorted(
            [row for row in rows if row.get("delta_pct") is not None],
            key=lambda row: abs(row["delta_pct"]),
            reverse=True,
        )

        for row in sorted_rows[:5]:
            direction = "aumentó" if row["delta_pct"] > 0 else "disminuyó"

            insights.append(
                f"{row['label']} {direction} {abs(row['delta_pct'])}% "
                f"respecto al periodo anterior."
            )

        return insights

    @staticmethod
    def _generate_warnings(raw_rows: List[dict], clean_rows: List[dict]) -> List[str]:
        warnings = []

        discarded = len(raw_rows) - len(clean_rows)

        if discarded > 0:
            warnings.append(
                f"Se descartaron {discarded} filas por inconsistencias numéricas o etiquetas no válidas."
            )

        if not clean_rows:
            warnings.append("No se encontraron datos financieros válidos para generar analítica.")

        return warnings