import re
from collections import defaultdict

from app.schemas.analytics import (
    AnalyticsMetric,
    AnalyticsResult,
    ChartPoint,
    ChartSeries,
    ChartSpec,
)


class AnalyticsService:
    NUMBER_PATTERN = re.compile(
        r"(?P<label>[A-Za-zÁÉÍÓÚáéíóúÑñ0-9_\-/\s]{2,80})[:\-]\s*(?P<value>\d[\d\.,]*)\s*(?P<suffix>%|€|eur|usd|k|m|millones|miles)?",
        re.IGNORECASE,
    )

    QUARTER_PATTERN = re.compile(
        r"\b(Q[1-4]|T[1-4]|(?:1er|2do|3er|4to)\s+trimestre|trimestre\s+[1-4])\b",
        re.IGNORECASE,
    )

    YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")

    MONTH_PATTERN = re.compile(
        r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b",
        re.IGNORECASE,
    )

    def analyze(self, text: str, document_type: str) -> dict:
        lines = self._normalize_lines(text)

        metrics: list[AnalyticsMetric] = []
        percentages: list[AnalyticsMetric] = []

        for line in lines:
            match = self.NUMBER_PATTERN.search(line)
            if not match:
                continue

            label = self._clean_label(match.group("label"))
            raw_value = match.group("value")
            suffix = (match.group("suffix") or "").lower()

            numeric_value = self._parse_number(raw_value)
            if numeric_value is None:
                continue

            normalized_value = self._apply_suffix(numeric_value, suffix)

            metric = AnalyticsMetric(
                label=label,
                value=normalized_value,
                raw_value=f"{raw_value}{match.group('suffix') or ''}",
                context=line,
            )

            if suffix == "%":
                percentages.append(metric)
            else:
                metrics.append(metric)

        chart_specs = self._generate_chart_specs(metrics, percentages, document_type)

        warnings = []
        if not metrics and not percentages:
            warnings.append(
                "No se detectaron suficientes líneas con estructura numérica clara para generar analítica útil."
            )

        return AnalyticsResult(
            document_type=document_type,
            metrics=metrics[:25],
            percentages=percentages[:25],
            chart_specs=chart_specs,
            warnings=warnings,
            metadata={
                "metrics_detected": len(metrics),
                "percentages_detected": len(percentages),
                "chart_specs_generated": len(chart_specs),
            },
        ).model_dump()

    @staticmethod
    def _normalize_lines(text: str) -> list[str]:
        raw_lines = text.splitlines()
        cleaned_lines = []

        for line in raw_lines:
            normalized = " ".join(line.strip().split())
            if len(normalized) >= 4:
                cleaned_lines.append(normalized)

        return cleaned_lines

    @staticmethod
    def _clean_label(label: str) -> str:
        return " ".join(label.strip(" -:_").split())

    @staticmethod
    def _parse_number(raw_value: str) -> float | None:
        candidate = raw_value.strip().replace(" ", "")

        if "," in candidate and "." in candidate:
            if candidate.rfind(",") > candidate.rfind("."):
                candidate = candidate.replace(".", "").replace(",", ".")
            else:
                candidate = candidate.replace(",", "")
        elif candidate.count(",") == 1 and candidate.count(".") == 0:
            candidate = candidate.replace(",", ".")
        else:
            candidate = candidate.replace(",", "")

        try:
            return float(candidate)
        except ValueError:
            return None

    @staticmethod
    def _apply_suffix(value: float, suffix: str) -> float:
        suffix = suffix.lower()

        if suffix in {"k"}:
            return value * 1000
        if suffix in {"m", "millones"}:
            return value * 1_000_000
        if suffix in {"miles"}:
            return value * 1000

        return value

    def _generate_chart_specs(
        self,
        metrics: list[AnalyticsMetric],
        percentages: list[AnalyticsMetric],
        document_type: str,
    ) -> list[ChartSpec]:
        chart_specs: list[ChartSpec] = []

        category_chart = self._build_category_bar_chart(metrics)
        if category_chart:
            chart_specs.append(category_chart)

        time_chart = self._build_time_chart(metrics)
        if time_chart:
            chart_specs.append(time_chart)

        percentage_chart = self._build_percentage_chart(percentages)
        if percentage_chart:
            chart_specs.append(percentage_chart)

        if document_type == "business_report" and not chart_specs and metrics:
            fallback = self._build_fallback_bar_chart(metrics)
            if fallback:
                chart_specs.append(fallback)

        return chart_specs

    def _build_category_bar_chart(self, metrics: list[AnalyticsMetric]) -> ChartSpec | None:
        valid_metrics = [
            metric for metric in metrics
            if not self._looks_temporal(metric.label)
        ]

        if len(valid_metrics) < 3:
            return None

        unique_labels = []
        seen = set()

        for metric in valid_metrics:
            lowered = metric.label.lower()
            if lowered not in seen:
                seen.add(lowered)
                unique_labels.append(metric)

        if len(unique_labels) < 3:
            return None

        selected = unique_labels[:8]

        return ChartSpec(
            chart_type="bar",
            title="Comparativa de métricas detectadas",
            x_label="Categoría",
            y_label="Valor",
            series=[
                ChartSeries(
                    name="Métricas",
                    data=[ChartPoint(x=item.label, y=item.value) for item in selected],
                )
            ],
            reason="Se detectaron varias métricas con etiquetas diferenciadas, adecuadas para una comparativa por categorías.",
        )

    def _build_time_chart(self, metrics: list[AnalyticsMetric]) -> ChartSpec | None:
        temporal_items = []

        for metric in metrics:
            if self._looks_temporal(metric.label) or self._looks_temporal(metric.context or ""):
                temporal_items.append(metric)

        if len(temporal_items) < 2:
            return None

        selected = temporal_items[:12]

        return ChartSpec(
            chart_type="line",
            title="Evolución temporal detectada",
            x_label="Periodo",
            y_label="Valor",
            series=[
                ChartSeries(
                    name="Serie temporal",
                    data=[ChartPoint(x=item.label, y=item.value) for item in selected],
                )
            ],
            reason="Se detectaron referencias a periodos o series temporales, por lo que una line chart tiene sentido.",
        )

    def _build_percentage_chart(self, percentages: list[AnalyticsMetric]) -> ChartSpec | None:
        if len(percentages) < 2:
            return None

        selected = percentages[:6]

        return ChartSpec(
            chart_type="bar",
            title="Porcentajes detectados",
            x_label="Indicador",
            y_label="Porcentaje",
            series=[
                ChartSeries(
                    name="Porcentajes",
                    data=[ChartPoint(x=item.label, y=item.value) for item in selected],
                )
            ],
            reason="Se detectaron varios porcentajes explícitos; se representan mejor como bar chart que como pie chart en esta fase.",
        )

    def _build_fallback_bar_chart(self, metrics: list[AnalyticsMetric]) -> ChartSpec | None:
        selected = metrics[:5]

        if len(selected) < 2:
            return None

        return ChartSpec(
            chart_type="bar",
            title="Resumen visual de métricas detectadas",
            x_label="Métrica",
            y_label="Valor",
            series=[
                ChartSeries(
                    name="Datos detectados",
                    data=[ChartPoint(x=item.label, y=item.value) for item in selected],
                )
            ],
            reason="Se generó un gráfico de respaldo porque se detectaron métricas numéricas, aunque no suficiente estructura para una clasificación más específica.",
        )

    def _looks_temporal(self, text: str) -> bool:
        lowered = text.lower()

        if self.QUARTER_PATTERN.search(lowered):
            return True
        if self.YEAR_PATTERN.search(lowered):
            return True
        if self.MONTH_PATTERN.search(lowered):
            return True

        return False