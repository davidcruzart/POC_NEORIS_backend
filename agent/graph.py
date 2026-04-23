from langgraph.graph import END, StateGraph

from app.agent.nodes import build_nodes
from app.agent.routers import route_by_intent
from app.agent.state import AgentState
from app.implementations.summarizers.openai_summarizer import OpenAISummarizer
from app.services.analytics_service import AnalyticsService
from app.services.classification_service import ClassificationService
from app.services.summary_service import SummaryService


def build_agent_graph():
    summarizer = OpenAISummarizer()
    summary_service = SummaryService(summarizer=summarizer)
    classification_service = ClassificationService()
    analytics_service = AnalyticsService()

    nodes = build_nodes(
        summary_service=summary_service,
        classification_service=classification_service,
        analytics_service=analytics_service,
    )

    builder = StateGraph(AgentState)

    builder.add_node("classify_document", nodes["classify_document"])
    builder.add_node("classify_user_intent", nodes["classify_user_intent"])
    builder.add_node("summarize", nodes["summarize"])
    builder.add_node("extract_analytics", nodes["extract_analytics"])

    builder.set_entry_point("classify_document")
    builder.add_edge("classify_document", "classify_user_intent")

    builder.add_conditional_edges(
        "classify_user_intent",
        route_by_intent,
        {
            "summarize": "summarize",
            "extract_analytics": "extract_analytics",
        },
    )

    builder.add_edge("summarize", END)
    builder.add_edge("extract_analytics", END)

    return builder.compile()