from app.core.constants import DOCUMENT_TYPES, USER_INTENTS


class ClassificationService:
    def classify_document(self, text: str) -> str:
        lowered_text = text.lower()

        if any(
            word in lowered_text
            for word in [
                "empresa",
                "ingresos",
                "beneficios",
                "costes",
                "clientes",
                "ventas",
                "facturación",
                "margen",
                "ebitda",
                "mercado",
                "unidades vendidas",
            ]
        ):
            return "business_report"

        if any(
            word in lowered_text
            for word in [
                "metodología",
                "referencias",
                "abstract",
                "hipótesis",
                "conclusiones",
                "bibliografía",
            ]
        ):
            return "academic"

        if any(
            word in lowered_text
            for word in [
                "requisito",
                "arquitectura",
                "api",
                "backend",
                "frontend",
                "microservicio",
                "endpoint",
                "base de datos",
            ]
        ):
            return "project_documentation"

        if any(
            word in lowered_text
            for word in [
                "capítulo",
                "personaje",
                "novela",
                "relato",
                "protagonista",
            ]
        ):
            return "novel"

        return "generic"

    def classify_user_intent(self, user_request: str | None = None) -> str:
        if not user_request:
            return "summarize"

        lowered_request = user_request.lower()

        if any(term in lowered_request for term in ["analytics", "analítica", "estadísticas", "graficas", "gráficas", "metricas", "métricas", "datos"]):
            return "extract_analytics"

        if "riesgo" in lowered_request or "risk" in lowered_request:
            return "extract_risks"

        if "acción" in lowered_request or "acciones" in lowered_request or "action" in lowered_request:
            return "extract_actions"

        if "keyword" in lowered_request or "palabra clave" in lowered_request or "keywords" in lowered_request:
            return "extract_keywords"

        if "pregunta" in lowered_request or "question" in lowered_request:
            return "generate_questions"

        if "compar" in lowered_request:
            return "compare_documents"

        if "qa" in lowered_request or "pregunta sobre" in lowered_request:
            return "qa"

        return "summarize"

    @staticmethod
    def validate_document_type(document_type: str) -> str:
        if document_type not in DOCUMENT_TYPES:
            return "generic"
        return document_type

    @staticmethod
    def validate_user_intent(user_intent: str) -> str:
        if user_intent not in USER_INTENTS:
            return "summarize"
        return user_intent