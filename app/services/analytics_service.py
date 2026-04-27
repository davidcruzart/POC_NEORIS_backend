import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import DEFAULT_MODEL_NAME
from app.prompts.analytics_prompts import ANALYTICS_INSIGHTS_PROMPT
from app.schemas.analytics import ChartPoint, ChartSeries, ChartSpec


class AnalyticsService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        )
        self.insights_prompt = ChatPromptTemplate.from_template(
            ANALYTICS_INSIGHTS_PROMPT
        )

    def analyze(self, text: str, document_type: str) -> dict:
        rows = self._extract_financial_rows(text)
        chart_specs = self._build_chart_specs(rows)
        insights = self._generate_insights(rows)

        warnings = []

        if not rows:
            warnings.append(
                "No se pudieron extraer filas financieras estructuradas del documento."
            )

        if rows and not chart_specs:
            warnings.append(
                "Se extrajeron métricas financieras, pero no suficientes datos agrupables para generar gráficas útiles."
            )

        return {
            "document_type": document_type,
            "rows": rows,
            "metrics": self._build_metrics_preview(rows),
            "percentages": self._build_percentages_preview(rows),
            "chart_specs": chart_specs,
            "insights": insights,
            "warnings": warnings,
            "metadata": {
                "rows_detected": len(rows),
                "chart_specs_generated": len(chart_specs),
                "insights_generated": len(insights),
            },
        }

    # ---------------------------------------------------------
    # MAIN EXTRACTION
    # ---------------------------------------------------------

    def _extract_financial_rows(self, text: str) -> list[dict[str, Any]]:
        sections = self._split_financial_sections(text)

        rows: list[dict[str, Any]] = []

        for statement, section_text in sections.items():
            rows.extend(self._extract_rows_from_statement(statement, section_text))

        return self._deduplicate_rows(rows)

    def _split_financial_sections(self, text: str) -> dict[str, str]:
        markers = [
            ("income_statement", "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS"),
            ("balance_sheet", "CONDENSED CONSOLIDATED BALANCE SHEETS"),
            ("cash_flow", "CONDENSED CONSOLIDATED STATEMENTS OF CASH FLOWS"),
        ]

        upper_text = text.upper()
        positions = []

        for key, marker in markers:
            position = upper_text.find(marker)
            if position != -1:
                positions.append((key, position))

        positions.sort(key=lambda item: item[1])

        sections = {}

        for index, (key, start) in enumerate(positions):
            end = len(text)

            if index + 1 < len(positions):
                end = positions[index + 1][1]

            sections[key] = text[start:end]

        return sections

    def _extract_rows_from_statement(
        self,
        statement: str,
        statement_text: str,
    ) -> list[dict[str, Any]]:
        lines = self._normalize_lines(statement_text)
        unit = self._extract_unit(statement_text)
        periods = self._extract_periods(lines)

        current_section = "general"
        rows = []

        for line in lines:
            detected_section = self._detect_section(line, statement)

            if detected_section:
                current_section = detected_section
                continue

            parsed = self._parse_two_value_row(line)

            if not parsed:
                continue

            label, value_1, value_2 = parsed

            row = {
                "statement": statement,
                "section": current_section,
                "label": label,
                "period_1": periods[0] if len(periods) >= 1 else None,
                "value_1": value_1,
                "period_2": periods[1] if len(periods) >= 2 else None,
                "value_2": value_2,
                "unit": unit,
                "delta_abs": round(value_1 - value_2, 2),
                "delta_pct": self._calculate_delta_pct(value_1, value_2),
            }

            rows.append(row)

        return rows

    # ---------------------------------------------------------
    # TEXT NORMALIZATION
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_lines(text: str) -> list[str]:
        lines = []

        for raw_line in text.splitlines():
            line = " ".join(raw_line.strip().split())

            if line:
                lines.append(line)

        return lines

    @staticmethod
    def _extract_unit(text: str) -> str:
        lowered = text.lower()

        if "(in millions" in lowered:
            return "millions"

        if "(in thousands" in lowered:
            return "thousands"

        return "units"

    def _extract_periods(self, lines: list[str]) -> list[str]:
        periods = []
        max_scan = min(len(lines), 35)

        full_text = "\n".join(lines[:max_scan])

        direct_pattern = re.compile(
            r"(December|September|June|March)\s+\d{1,2},\s+\d{4}",
            re.IGNORECASE,
        )

        for match in direct_pattern.findall(full_text):
            pass

        direct_dates = re.findall(
            r"(?:December|September|June|March)\s+\d{1,2},\s+\d{4}",
            full_text,
            flags=re.IGNORECASE,
        )

        for date in direct_dates:
            normalized = self._normalize_period(date)
            if normalized not in periods:
                periods.append(normalized)

        if len(periods) >= 2:
            return periods[:2]

        # Caso típico en PDFs parseados:
        # December 27,
        # 2025
        split_dates = []

        for index, line in enumerate(lines[:max_scan]):
            if re.search(r"(December|September|June|March)\s+\d{1,2},$", line, re.IGNORECASE):
                if index + 1 < len(lines):
                    next_line = lines[index + 1]
                    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", next_line)

                    if year_match:
                        split_dates.append(f"{line} {year_match.group(1)}")

        for date in split_dates:
            normalized = self._normalize_period(date)
            if normalized not in periods:
                periods.append(normalized)

        return periods[:2]

    @staticmethod
    def _normalize_period(period: str) -> str:
        return " ".join(period.replace("\n", " ").split())

    # ---------------------------------------------------------
    # SECTIONS
    # ---------------------------------------------------------

    def _detect_section(self, line: str, statement: str) -> str | None:
        normalized = self._normalize_section_line(line)

        section_maps = {
            "income_statement": {
                "net sales": "net_sales",
                "cost of sales": "cost_of_sales",
                "operating expenses": "operating_expenses",
                "earnings per share": "earnings_per_share",
                "shares used in computing earnings per share": "shares_for_eps",
                "net sales by reportable segment": "net_sales_by_segment",
                "net sales by category": "net_sales_by_category",
            },
            "balance_sheet": {
                "assets": "assets",
                "current assets": "current_assets",
                "non-current assets": "non_current_assets",
                "liabilities and shareholders equity": "liabilities_and_equity",
                "current liabilities": "current_liabilities",
                "non-current liabilities": "non_current_liabilities",
                "shareholders equity": "shareholders_equity",
            },
            "cash_flow": {
                "operating activities": "operating_activities",
                "investing activities": "investing_activities",
                "financing activities": "financing_activities",
                "supplemental cash flow disclosure": "supplemental_cash_flow",
            },
        }

        for section_label, section_name in section_maps.get(statement, {}).items():
            if normalized == section_label:
                return section_name

        return None

    @staticmethod
    def _normalize_section_line(line: str) -> str:
        normalized = line.lower().strip()

        normalized = normalized.replace("’", "")
        normalized = normalized.replace("'", "")
        normalized = normalized.replace(":", "")
        normalized = normalized.replace("(1)", "")
        normalized = normalized.replace("/", " ")

        normalized = " ".join(normalized.split())

        return normalized

    # ---------------------------------------------------------
    # ROW PARSING
    # ---------------------------------------------------------

    def _parse_two_value_row(self, line: str) -> tuple[str, float, float] | None:
        cleaned = line

        cleaned = cleaned.replace("$", "")
        cleaned = cleaned.replace("(", "-")
        cleaned = cleaned.replace(")", "")
        cleaned = cleaned.replace("—", "-")

        match = re.match(
            r"^(?P<label>.+?)\s+(?P<value_1>-?\d[\d,]*\.?\d*)\s+(?P<value_2>-?\d[\d,]*\.?\d*)$",
            cleaned,
        )

        if not match:
            return None

        label = match.group("label").strip(" :-")
        value_1 = self._parse_number(match.group("value_1"))
        value_2 = self._parse_number(match.group("value_2"))

        if value_1 is None or value_2 is None:
            return None

        if self._should_skip_label(label):
            return None

        return label, value_1, value_2

    @staticmethod
    def _parse_number(value: str) -> float | None:
        candidate = value.replace(",", "").strip()

        try:
            return float(candidate)
        except ValueError:
            return None

    @staticmethod
    def _calculate_delta_pct(value_1: float, value_2: float) -> float | None:
        if value_2 == 0:
            return None

        return round(((value_1 - value_2) / value_2) * 100, 2)

    @staticmethod
    def _should_skip_label(label: str) -> bool:
        lowered = label.lower()

        noise_patterns = [
            "apple inc",
            "three months ended",
            "december",
            "september",
            "in millions",
            "in thousands",
            "unaudited",
            "except number",
            "par value",
            "authorized",
            "issued and outstanding",
        ]

        if any(pattern in lowered for pattern in noise_patterns):
            return True

        if len(label.strip()) < 2:
            return True

        return False

    @staticmethod
    def _deduplicate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        result = []

        for row in rows:
            key = (
                row["statement"],
                row["section"],
                row["label"],
                row["period_1"],
                row["period_2"],
                row["value_1"],
                row["value_2"],
            )

            if key not in seen:
                seen.add(key)
                result.append(row)

        return result

    # ---------------------------------------------------------
    # PREVIEWS
    # ---------------------------------------------------------

    @staticmethod
    def _build_metrics_preview(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "label": row["label"],
                "value": row["value_1"],
                "raw_value": str(row["value_1"]),
                "context": f"{row['statement']} / {row['section']} / {row['period_1']}",
            }
            for row in rows[:30]
        ]

    @staticmethod
    def _build_percentages_preview(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        percentages = []

        for row in rows:
            if row["delta_pct"] is None:
                continue

            percentages.append(
                {
                    "label": f"{row['label']} variation",
                    "value": row["delta_pct"],
                    "raw_value": f"{row['delta_pct']}%",
                    "context": f"{row['period_1']} vs {row['period_2']}",
                }
            )

        return percentages[:30]

    # ---------------------------------------------------------
    # CHARTS
    # ---------------------------------------------------------

    def _build_chart_specs(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chart_specs = []

        for chart in [
            self._build_kpi_chart(rows),
            self._build_revenue_category_chart(rows),
            self._build_revenue_segment_chart(rows),
            self._build_cashflow_chart(rows),
            self._build_delta_pct_chart(rows),
        ]:
            if chart:
                chart_specs.append(chart)

        return chart_specs

    def _build_kpi_chart(self, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        wanted = {
            "Total net sales",
            "Gross margin",
            "Operating income",
            "Net income",
        }

        selected = [
            row for row in rows
            if row["statement"] == "income_statement"
            and row["label"] in wanted
        ]

        return self._build_two_period_bar_chart(
            selected,
            title="Key financial metrics",
            x_label="Metric",
            y_label="Value",
            reason="Main income statement KPIs compared across both periods.",
        )

    def _build_revenue_category_chart(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        selected = [
            row for row in rows
            if row["statement"] == "income_statement"
            and row["section"] == "net_sales_by_category"
            and "total" not in row["label"].lower()
        ]

        return self._build_two_period_bar_chart(
            selected,
            title="Net sales by category",
            x_label="Category",
            y_label="Net sales",
            reason="Revenue breakdown by product and services category.",
        )

    def _build_revenue_segment_chart(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        selected = [
            row for row in rows
            if row["statement"] == "income_statement"
            and row["section"] == "net_sales_by_segment"
            and "total" not in row["label"].lower()
        ]

        return self._build_two_period_bar_chart(
            selected,
            title="Net sales by reportable segment",
            x_label="Segment",
            y_label="Net sales",
            reason="Revenue breakdown by geographic/reportable segment.",
        )

    def _build_cashflow_chart(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        wanted = {
            "Cash generated by operating activities",
            "Cash generated by/(used in) investing activities",
            "Cash used in financing activities",
        }

        selected = [
            row for row in rows
            if row["statement"] == "cash_flow"
            and row["label"] in wanted
        ]

        return self._build_two_period_bar_chart(
            selected,
            title="Cash flow by activity",
            x_label="Activity",
            y_label="Cash flow",
            reason="Comparison of operating, investing and financing cash flows.",
        )

    def _build_delta_pct_chart(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        important_rows = [
            row for row in rows
            if row["delta_pct"] is not None
            and row["statement"] == "income_statement"
            and row["section"] in {
                "net_sales_by_category",
                "net_sales_by_segment",
                "general",
                "net_sales",
            }
            and "total" not in row["label"].lower()
        ]

        important_rows = important_rows[:10]

        if len(important_rows) < 2:
            return None

        return ChartSpec(
            chart_type="bar",
            title="Percentage variation by metric",
            x_label="Metric",
            y_label="Variation (%)",
            series=[
                ChartSeries(
                    name="Variation %",
                    data=[
                        ChartPoint(
                            x=row["label"],
                            y=row["delta_pct"],
                        )
                        for row in important_rows
                    ],
                )
            ],
            reason="Shows percentage changes between both periods.",
        ).model_dump()

    @staticmethod
    def _build_two_period_bar_chart(
        rows: list[dict[str, Any]],
        title: str,
        x_label: str,
        y_label: str,
        reason: str,
    ) -> dict[str, Any] | None:
        if len(rows) < 2:
            return None

        period_1 = rows[0].get("period_1") or "Current period"
        period_2 = rows[0].get("period_2") or "Previous period"

        return ChartSpec(
            chart_type="bar",
            title=title,
            x_label=x_label,
            y_label=y_label,
            series=[
                ChartSeries(
                    name=period_1,
                    data=[
                        ChartPoint(x=row["label"], y=row["value_1"])
                        for row in rows
                    ],
                ),
                ChartSeries(
                    name=period_2,
                    data=[
                        ChartPoint(x=row["label"], y=row["value_2"])
                        for row in rows
                    ],
                ),
            ],
            reason=reason,
        ).model_dump()

    # ---------------------------------------------------------
    # LLM INSIGHTS
    # ---------------------------------------------------------

    def _generate_insights(self, rows: list[dict[str, Any]]) -> list[str]:
        if not rows:
            return []

        compact_rows = self._select_rows_for_insights(rows)

        if not compact_rows:
            return []

        try:
            chain = self.insights_prompt | self.llm

            response = chain.invoke(
                {
                    "datos": json.dumps(
                        compact_rows,
                        ensure_ascii=False,
                        indent=2,
                    )
                }
            )

            return self._parse_insights_response(response.content)

        except Exception:
            return []

    @staticmethod
    def _select_rows_for_insights(
        rows: list[dict[str, Any]],
        max_rows: int = 25,
    ) -> list[dict[str, Any]]:
        priority_labels = {
            "Total net sales",
            "Gross margin",
            "Operating income",
            "Net income",
            "iPhone",
            "Services",
            "Americas",
            "Europe",
            "Greater China",
            "Cash generated by operating activities",
            "Cash used in financing activities",
        }

        selected = [
            row for row in rows
            if row["label"] in priority_labels
        ]

        if len(selected) < 5:
            selected = rows[:max_rows]

        return selected[:max_rows]

    @staticmethod
    def _parse_insights_response(content: str) -> list[str]:
        if not content:
            return []

        lines = []

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            line = re.sub(r"^\d+[\).\s-]+", "", line)
            line = line.strip("-• ")

            if line:
                lines.append(line)

        return lines[:6]