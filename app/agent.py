from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.services.analytics_service import AnalyticsService
from app.services.classification_service import ClassificationService
from app.services.comparison_service import ComparisonService
from app.services.qa_service import QAService
from app.services.summary_service import SummaryService


class AgentState(TypedDict, total=False):
    raw_text: str
    file_bytes: Optional[bytes]
    filename: Optional[str]

    second_raw_text: Optional[str]
    second_file_bytes: Optional[bytes]
    second_filename: Optional[str]

    user_request: Optional[str]
    percentage: int

    document_type: str
    user_intent: str

    summary_result: Dict[str, Any]
    analytics_result: Dict[str, Any]
    comparison_result: Dict[str, Any]
    qa_result: Dict[str, Any]

    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]


class Agent:
    def __init__(
        self,
        summary_service: SummaryService,
        classification_service: ClassificationService,
        analytics_service: AnalyticsService,
        comparison_service: ComparisonService,
        qa_service: QAService,
    ):
        self.summary_service = summary_service
        self.classification_service = classification_service
        self.analytics_service = analytics_service
        self.comparison_service = comparison_service
        self.qa_service = qa_service
        self.graph = self._build_graph()

    def run(self, initial_state: dict) -> dict:
        return self.graph.invoke(initial_state)

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("classify_document", self._classify_document_node)
        builder.add_node("classify_user_intent", self._classify_user_intent_node)
        builder.add_node("summarize", self._summarize_node)
        builder.add_node("extract_analytics", self._extract_analytics_node)
        builder.add_node("compare_documents", self._compare_documents_node)
        builder.add_node("qa_rag", self._qa_rag_node)

        builder.set_entry_point("classify_document")

        builder.add_edge("classify_document", "classify_user_intent")

        builder.add_conditional_edges(
            "classify_user_intent",
            self._route_by_intent,
            {
                "summarize": "summarize",
                "extract_analytics": "extract_analytics",
                "compare_documents": "compare_documents",
                "qa_rag": "qa_rag",
            },
        )

        builder.add_edge("summarize", END)
        builder.add_edge("extract_analytics", END)
        builder.add_edge("compare_documents", END)
        builder.add_edge("qa_rag", END)

        return builder.compile()

    def _classify_document_node(self, state: dict) -> dict:
        document_type = self.classification_service.classify_document(
            state["raw_text"]
        )

        state["document_type"] = self.classification_service.validate_document_type(
            document_type
        )

        state.setdefault("metadata", {})["document_classified"] = True

        return state

    def _classify_user_intent_node(self, state: dict) -> dict:
        user_intent = self.classification_service.classify_user_intent(
            state.get("user_request")
        )

        state["user_intent"] = self.classification_service.validate_user_intent(
            user_intent
        )

        state.setdefault("metadata", {})["intent_classified"] = True

        return state

    def _summarize_node(self, state: dict) -> dict:
        percentage = state.get("percentage", 30)

        if not percentage or percentage <= 0:
            percentage = 30

        result = self.summary_service.summarize_text(
            text=state["raw_text"],
            percentage=percentage,
        )

        state["summary_result"] = result

        state.setdefault("metadata", {}).update(
            {
                "executed_tool": "summarize",
            }
        )

        return state

    def _extract_analytics_node(self, state: dict) -> dict:
        result = self.analytics_service.analyze(
            raw_text=state["raw_text"],
            document_type=state["document_type"],
            file_bytes=state.get("file_bytes"),
        )

        state["analytics_result"] = result

        analytics_warnings = result.get("warnings", [])
        if analytics_warnings:
            state.setdefault("warnings", []).extend(analytics_warnings)

        state.setdefault("metadata", {}).update(
            {
                "executed_tool": "extract_analytics",
                "analytics_generated": True,
                "chart_specs_generated": result.get("metadata", {}).get(
                    "chart_specs_generated",
                    0,
                ),
            }
        )

        return state

    def _compare_documents_node(self, state: dict) -> dict:
        second_raw_text = state.get("second_raw_text")

        if not second_raw_text:
            state.setdefault("errors", []).append(
                "La comparación requiere un segundo documento."
            )
            state.setdefault("metadata", {}).update(
                {
                    "executed_tool": "compare_documents",
                    "comparison_generated": False,
                }
            )
            return state

        result = self.comparison_service.compare_documents(
            text_a=state["raw_text"],
            text_b=second_raw_text,
            user_request=state.get("user_request"),
        )

        state["comparison_result"] = result

        state.setdefault("metadata", {}).update(
            {
                "executed_tool": "compare_documents",
                "comparison_generated": True,
            }
        )

        return state

    def _qa_rag_node(self, state: dict) -> dict:
        question = state.get("user_request") or "Responde usando el contenido del documento."

        result = self.qa_service.answer_question(
            text=state["raw_text"],
            question=question,
        )

        state["qa_result"] = result

        state.setdefault("metadata", {}).update(
            {
                "executed_tool": "qa_rag",
                "qa_generated": True,
            }
        )

        return state

    @staticmethod
    def _route_by_intent(state: dict) -> str:
        user_intent = state.get("user_intent", "summarize")

        if user_intent == "extract_analytics":
            return "extract_analytics"

        if user_intent == "compare_documents":
            return "compare_documents"

        if user_intent == "qa_rag":
            return "qa_rag"

        return "summarize"