from app.agent.tools import (
    classify_document_tool,
    classify_intent_tool,
    extract_analytics_tool,
    summarize_tool,
)
from app.services.analytics_service import AnalyticsService
from app.services.classification_service import ClassificationService
from app.services.summary_service import SummaryService


def build_nodes(
    summary_service: SummaryService,
    classification_service: ClassificationService,
    analytics_service: AnalyticsService,
) -> dict:
    def classify_document_node(state: dict) -> dict:
        return classify_document_tool(state, classification_service)

    def classify_user_intent_node(state: dict) -> dict:
        return classify_intent_tool(state, classification_service)

    def summarize_node(state: dict) -> dict:
        return summarize_tool(state, summary_service)

    def extract_analytics_node(state: dict) -> dict:
        return extract_analytics_tool(state, analytics_service)

    return {
        "classify_document": classify_document_node,
        "classify_user_intent": classify_user_intent_node,
        "summarize": summarize_node,
        "extract_analytics": extract_analytics_node,
    }