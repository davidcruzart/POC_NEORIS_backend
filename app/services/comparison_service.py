import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import DEFAULT_MODEL_NAME


class ComparisonService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        )

        self.keyword_prompt = ChatPromptTemplate.from_template(
            """
Extrae entre 8 y 15 palabras clave o conceptos principales del siguiente documento.

Reglas:
- Devuelve solo una lista JSON de strings.
- No expliques nada.
- No inventes conceptos que no estén en el texto.

Documento:
{texto}
"""
        )

        self.summary_prompt = ChatPromptTemplate.from_template(
            """
Resume brevemente el siguiente documento para poder compararlo con otro.

Reglas:
- Máximo 250 palabras.
- Mantén datos, temas y conclusiones importantes.
- No inventes información.

Documento:
{texto}
"""
        )

        self.comparison_prompt = ChatPromptTemplate.from_template(
            """
Compara los dos documentos usando sus resúmenes y palabras clave.

Documento A - resumen:
{summary_a}

Documento A - keywords:
{keywords_a}

Documento B - resumen:
{summary_b}

Documento B - keywords:
{keywords_b}

Devuelve un JSON válido con esta estructura exacta:

{{
  "similarities": ["..."],
  "differences": ["..."],
  "comparison_summary": "..."
}}

Reglas:
- No inventes información.
- Si algo no está claro, indícalo de forma prudente.
- Las similitudes y diferencias deben ser concretas.
"""
        )

    def compare_documents(
        self,
        text_a: str,
        text_b: str,
        user_request: str | None = None,
    ) -> dict[str, Any]:
        summary_a = self._summarize_for_comparison(text_a)
        summary_b = self._summarize_for_comparison(text_b)

        keywords_a = self._extract_keywords(text_a)
        keywords_b = self._extract_keywords(text_b)

        comparison_payload = self._compare(
            summary_a=summary_a,
            summary_b=summary_b,
            keywords_a=keywords_a,
            keywords_b=keywords_b,
        )

        return {
            "document_a_summary": summary_a,
            "document_b_summary": summary_b,
            "document_a_keywords": keywords_a,
            "document_b_keywords": keywords_b,
            "similarities": comparison_payload.get("similarities", []),
            "differences": comparison_payload.get("differences", []),
            "comparison_summary": comparison_payload.get("comparison_summary"),
            "metadata": {
                "user_request": user_request,
                "document_a_chars": len(text_a),
                "document_b_chars": len(text_b),
            },
        }

    def _summarize_for_comparison(self, text: str) -> str:
        excerpt = self._build_excerpt(text, max_chars=20_000)
        chain = self.summary_prompt | self.llm
        response = chain.invoke({"texto": excerpt})
        return str(response.content).strip()

    def _extract_keywords(self, text: str) -> list[str]:
        excerpt = self._build_excerpt(text, max_chars=20_000)
        chain = self.keyword_prompt | self.llm
        response = chain.invoke({"texto": excerpt})

        content = str(response.content).strip()

        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass

        return [
            item.strip(" -•\t")
            for item in content.splitlines()
            if item.strip(" -•\t")
        ][:15]

    def _compare(
        self,
        summary_a: str,
        summary_b: str,
        keywords_a: list[str],
        keywords_b: list[str],
    ) -> dict[str, Any]:
        chain = self.comparison_prompt | self.llm
        response = chain.invoke(
            {
                "summary_a": summary_a,
                "summary_b": summary_b,
                "keywords_a": ", ".join(keywords_a),
                "keywords_b": ", ".join(keywords_b),
            }
        )

        content = str(response.content).strip()

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        return {
            "similarities": [],
            "differences": [],
            "comparison_summary": content,
        }

    @staticmethod
    def _build_excerpt(text: str, max_chars: int) -> str:
        clean_text = (text or "").strip()

        if len(clean_text) <= max_chars:
            return clean_text

        head_size = max_chars // 2
        tail_size = max_chars - head_size

        return (
            clean_text[:head_size]
            + "\n\n[... CONTENIDO INTERMEDIO OMITIDO ...]\n\n"
            + clean_text[-tail_size:]
        )