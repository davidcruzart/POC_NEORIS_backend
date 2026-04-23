from app.services.analytics_service import AnalyticsService
from app.services.classification_service import ClassificationService
from app.services.summary_service import SummaryService


def classify_document_tool(state: dict, classification_service: ClassificationService) -> dict:
    document_type = classification_service.classify_document(state["raw_text"])
    state["document_type"] = classification_service.validate_document_type(document_type)
    return state


def classify_intent_tool(state: dict, classification_service: ClassificationService) -> dict:
    user_intent = classification_service.classify_user_intent(state.get("user_request"))
    state["user_intent"] = classification_service.validate_user_intent(user_intent)
    return state


def summarize_tool(state: dict, summary_service: SummaryService) -> dict:
    result = summary_service.summarize_text(
        text=state["raw_text"],
        percentage=state["percentage"],
    )
    state["summary_result"] = result
    return state


def extract_analytics_tool(state: dict, analytics_service: AnalyticsService) -> dict:
    result = analytics_service.analyze(
        text=state["raw_text"],
        document_type=state["document_type"],
    )
    state["analytics_result"] = result

    analytics_warnings = result.get("warnings", [])
    if analytics_warnings:
        state.setdefault("warnings", []).extend(analytics_warnings)

    state.setdefault("metadata", {}).update({
        "analytics_generated": True,
        "chart_specs_generated": result.get("metadata", {}).get("chart_specs_generated", 0),
    })
    return state