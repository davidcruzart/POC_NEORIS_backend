import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import DEFAULT_MODEL_NAME
from app.prompts.comparison_prompts import DOCUMENT_COMPARISON_PROMPT
from app.schemas.comparison import ComparisonExtraction

logger = logging.getLogger(__name__)


class ComparisonService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        ).with_structured_output(ComparisonExtraction)

        self.prompt = ChatPromptTemplate.from_template(
            DOCUMENT_COMPARISON_PROMPT
        )

    def compare_documents(
        self,
        text_a: str,
        text_b: str,
        user_request: str | None = None,
        filename_a: str | None = None,
        filename_b: str | None = None,
    ) -> dict[str, Any]:
        text_a = str(text_a or "").strip()
        text_b = str(text_b or "").strip()
        user_request = str(user_request or "Compara estos dos documentos.").strip()

        if not text_a:
            return self._empty_result(
                warnings=["El documento A no contiene texto extraído."],
                filename_a=filename_a,
                filename_b=filename_b,
            )

        if not text_b:
            return self._empty_result(
                warnings=["El documento B no contiene texto extraído."],
                filename_a=filename_a,
                filename_b=filename_b,
            )

        try:
            chain = self.prompt | self.llm

            result = chain.invoke(
                {
                    "document_a": text_a[:60_000],
                    "document_b": text_b[:60_000],
                    "user_request": user_request,
                }
            )

            return {
                "document_a_summary": result.document_a_summary,
                "document_b_summary": result.document_b_summary,
                "document_a_keywords": self._clean_list(result.document_a_keywords),
                "document_b_keywords": self._clean_list(result.document_b_keywords),
                "similarities": self._clean_list(result.similarities),
                "differences": self._clean_list(result.differences),
                "document_a_advantages": self._clean_list(result.document_a_advantages),
                "document_a_disadvantages": self._clean_list(result.document_a_disadvantages),
                "document_b_advantages": self._clean_list(result.document_b_advantages),
                "document_b_disadvantages": self._clean_list(result.document_b_disadvantages),
                "comparison_summary": result.comparison_summary,
                "metadata": {
                    "method": "structured_llm_document_comparison",
                    "filename_a": filename_a,
                    "filename_b": filename_b,
                    "document_a_chars_used": min(len(text_a), 60_000),
                    "document_b_chars_used": min(len(text_b), 60_000),
                },
            }

        except Exception as exc:
            logger.error("Error comparando documentos: %s", exc)

            return self._empty_result(
                warnings=[f"No se pudo generar la comparación: {exc}"],
                filename_a=filename_a,
                filename_b=filename_b,
            )

    @staticmethod
    def _clean_list(items: list[str]) -> list[str]:
        return [
            str(item).strip()
            for item in items or []
            if str(item).strip()
        ]

    @staticmethod
    def _empty_result(
        warnings: list[str],
        filename_a: str | None = None,
        filename_b: str | None = None,
    ) -> dict[str, Any]:
        return {
            "document_a_summary": None,
            "document_b_summary": None,
            "document_a_keywords": [],
            "document_b_keywords": [],
            "similarities": [],
            "differences": [],
            "document_a_advantages": [],
            "document_a_disadvantages": [],
            "document_b_advantages": [],
            "document_b_disadvantages": [],
            "comparison_summary": None,
            "metadata": {
                "method": "structured_llm_document_comparison",
                "filename_a": filename_a,
                "filename_b": filename_b,
                "warnings": warnings,
            },
        }