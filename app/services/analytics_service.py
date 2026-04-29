import json
import logging
import os
import tempfile
from typing import Any

import fitz  # PyMuPDF
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from markitdown import MarkItDown
from app.schemas.analytics import FinancialMetric
from app.schemas.analytics import AnalyticsExtraction, AnalyticsInsights
from pydantic import BaseModel, Field

from app.config import DEFAULT_MODEL_NAME
from app.prompts.analytics_prompts import (
    ANALYTICS_INSIGHTS_PROMPT,
    FINANCIAL_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self):
        self.markitdown = MarkItDown()
        self.extraction_llm = ChatOpenAI(model=DEFAULT_MODEL_NAME, temperature=0).with_structured_output(AnalyticsExtraction)
        self.insights_llm = ChatOpenAI(model=DEFAULT_MODEL_NAME, temperature=0).with_structured_output(AnalyticsInsights)
        self.extraction_prompt = ChatPromptTemplate.from_template(FINANCIAL_EXTRACTION_PROMPT)
        self.insights_prompt = ChatPromptTemplate.from_template(ANALYTICS_INSIGHTS_PROMPT)

    def analyze(self, raw_text: str, document_type: str, file_bytes: bytes | None = None, filename: str | None = None) -> dict[str, Any]:
        warnings = []
        raw_text = str(raw_text or "").strip()

        # Extraer contenido con triple fallback mejorado
        content = self._get_universal_content(raw_text, file_bytes, filename, warnings)

        # Log de depuración crítico
        preview = (content[:500] if content else "EMPTY_OR_NONE_OBJECT")
        logger.info(f"Analytics content preview (first 500 chars): {preview}")

        if not content or len(content.strip()) < 100 or content.lower() == "none":
            return self._empty_result(
                document_type=document_type,
                warnings=["No se pudo obtener texto legible para analítica financiera."],
                method="failed_extraction",
                filename=filename
            )

        extraction = self._extract_metrics(content)
        rows = self._build_rows(extraction.metrics)
        
        return {
            "document_type": document_type,
            "rows": rows,
            "metrics": self._build_metrics_preview(rows),
            "percentages": self._build_percentages_preview(rows),
            "chart_specs": self._build_chart_specs(rows),
            "insights": self._generate_insights(rows),
            "warnings": warnings if rows else warnings + ["No se detectaron métricas financieras claras."],
            "metadata": {
                "method": "universal_extraction_v2",
                "metrics_detected": len(rows),
                "source_filename": filename,
            },
        }

    def _get_universal_content(self, raw_text: str, file_bytes: bytes | None, filename: str | None, warnings: list[str]) -> str:
        if not file_bytes:
            return raw_text if not self._looks_like_binary_pdf(raw_text) else ""

        suffix = self._get_suffix(filename)
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(file_bytes)
                temp_path = f.name

            # CAPA 1: MarkItDown (con validación de calidad)
            try:
                result = self.markitdown.convert(temp_path)
                if result and result.text_content:
                    text = result.text_content.strip()
                    # VALIDACIÓN: Si es muy corto o dice "None", lo ignoramos y pasamos a Capa 2
                    if len(text) > 100 and text.lower() != "none" and not self._looks_like_binary_pdf(text):
                        logger.info("Capa 1: MarkItDown exitosa")
                        return text
            except Exception as e:
                logger.warning(f"Capa 1 (MarkItDown) falló: {e}")

            if suffix == ".pdf":
                text = self._extract_with_pymupdf(file_bytes)
                if len(text) > 100 and text.lower() != "none" and not self._looks_like_binary_pdf(text):
                    logger.info("Capa 2: PyMuPDF exitosa")
                    return text

            if raw_text and len(raw_text) > 100 and not self._looks_like_binary_pdf(raw_text):
                logger.info("Capa 3: Usando fallback de raw_text")
                return raw_text

            return ""

        except Exception as e:
            logger.error(f"Error en _get_universal_content: {e}")
            return ""
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def _extract_with_pymupdf(self, file_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            return "\n".join([page.get_text() for page in doc]).strip()
        except Exception as e:
            logger.warning(f"PyMuPDF falló: {e}")
            return ""

    @staticmethod
    def _looks_like_binary_pdf(text: str) -> bool:
        return str(text or "").lstrip().startswith("%PDF")

    @staticmethod
    def _get_suffix(filename: str | None) -> str:
        if filename and "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ".pdf"

    def _extract_metrics(self, content: str) -> AnalyticsExtraction:
        chain = self.extraction_prompt | self.extraction_llm
        try:
            return chain.invoke({"texto": content[:60_000]})
        except Exception as e:
            logger.error(f"Error LLM: {e}")
            return AnalyticsExtraction()

    def _build_rows(self, metrics: list[FinancialMetric]) -> list[dict[str, Any]]:
        rows = []
        seen = set()
        for m in metrics:
            label = (m.label or "").strip()
            if not label: continue
            v1, v2 = float(m.value_current), float(m.value_previous)
            key = (label.lower(), v1, v2)
            if key in seen: continue
            seen.add(key)
            rows.append({
                "statement": m.category, "section": m.category, "label": label,
                "period_1": m.period_current or "Actual", "value_1": v1,
                "period_2": m.period_previous or "Anterior", "value_2": v2,
                "unit": m.unit, "delta_abs": round(v1 - v2, 2),
                "delta_pct": None if v2 == 0 else round(((v1 - v2) / abs(v2)) * 100, 2),
            })
        return rows

    @staticmethod
    def _build_metrics_preview(rows):
        return [{"label": r["label"], "value": r["value_1"], "raw_value": str(r["value_1"]), "context": r.get("section")} for r in rows[:30]]

    @staticmethod
    def _build_percentages_preview(rows):
        return [{"label": f"{r['label']} var", "value": r["delta_pct"], "raw_value": f"{r['delta_pct']}%", "context": f"{r['period_1']} vs {r['period_2']}"} for r in rows if r.get("delta_pct") is not None][:30]

    def _build_chart_specs(self, rows):
        if not rows: return []
        top = rows[:10]
        return [{"title": "Comparativa Financiera", "chart_type": "bar", "series": [{"name": "Actual", "data": [{"x": r["label"], "y": r["value_1"]} for r in top]}, {"name": "Anterior", "data": [{"x": r["label"], "y": r["value_2"]} for r in top]}]}]

    def _generate_insights(self, rows: list[dict[str, Any]]) -> list[str]:
        """
        Genera insights de negocio utilizando el prompt ANALYTICS_INSIGHTS_PROMPT
        basándose en los datos estructurados y calculados.
        """
        if not rows:
            return []

        try:
            # IMPORTANTE: Creamos la cadena uniendo el prompt y el LLM con salida estructurada
            chain = self.insights_prompt | self.insights_llm
            
            # Convertimos las filas a JSON para que el LLM pueda procesarlas
            # Solo enviamos las primeras 30 para no saturar el contexto del modelo
            datos_json = json.dumps(rows[:30], ensure_ascii=False, indent=2)
            
            logger.info(f"Generando insights para {len(rows[:30])} métricas...")
            
            # Invocamos la cadena pasando la variable {datos} que espera tu prompt
            result = chain.invoke({"datos": datos_json})
            
            # Retornamos la lista de strings (insights) limitada a 6 elementos
            # result es una instancia de AnalyticsInsights (Pydantic)
            insights_limpios = [str(i).strip() for i in result.insights if i]
            
            return insights_limpios[:6]

        except Exception as e:
            logger.error(f"Error en la generación de insights financieros: {e}")
            # Si falla el LLM, podrías devolver insights básicos basados en lógica de código
            return self._generate_basic_insights(rows)

    @staticmethod
    def _generate_basic_insights(rows: list[dict[str, Any]]) -> list[str]:
        """Fallback manual si el LLM de insights falla."""
        insights = []
        # Ordenamos por mayor variación porcentual absoluta
        sorted_rows = sorted(
            [r for r in rows if r.get("delta_pct") is not None],
            key=lambda r: abs(r["delta_pct"]),
            reverse=True
        )
        for r in sorted_rows[:3]:
            dir_str = "aumentó" if r["delta_pct"] > 0 else "disminuyó"
            insights.append(f"La métrica '{r['label']}' {dir_str} un {abs(r['delta_pct'])}% respecto al periodo anterior.")
        
        return insights

    @staticmethod
    def _empty_result(document_type, warnings, method, filename):
        return {"document_type": document_type, "rows": [], "metrics": [], "percentages": [], "chart_specs": [], "insights": [], "warnings": warnings, "metadata": {"method": method, "source_filename": filename}}