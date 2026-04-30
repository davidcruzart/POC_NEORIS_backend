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

    document_id: Optional[str]

    user_request: Optional[str]
    percentage: int

    document_type: str
    user_intent: str

    summary_result: Dict[str, Any]
    analytics_result: Dict[str, Any]
    comparison_result: Dict[str, Any]
    qa_result: Dict[str, Any]
    qa_index_result: Dict[str, Any]

    chat_history: List[Dict[str, Any]]
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

        builder.add_node("prepare_request", self._prepare_request_node)
        builder.add_node("classify_document", self._classify_document_node)
        builder.add_node("classify_user_intent", self._classify_user_intent_node)

        builder.add_node("summarize", self._summarize_node)
        builder.add_node("extract_analytics", self._extract_analytics_node)
        builder.add_node("compare_documents", self._compare_documents_node)
        builder.add_node("qa_rag", self._qa_rag_node)
        builder.add_node("qa_index", self._qa_index_node)
        builder.add_node("qa_ask", self._qa_ask_node)

        builder.set_entry_point("prepare_request")

        builder.add_conditional_edges(
            "prepare_request",
            self._route_from_prepare,
            {
                "classify_document": "classify_document",
                "qa_ask": "qa_ask",
            },
        )

        builder.add_edge("classify_document", "classify_user_intent")

        builder.add_conditional_edges(
            "classify_user_intent",
            self._route_by_intent,
            {
                "summarize": "summarize",
                "extract_analytics": "extract_analytics",
                "compare_documents": "compare_documents",
                "qa_rag": "qa_rag",
                "qa_index": "qa_index",
                "qa_ask": "qa_ask",
            },
        )

        builder.add_edge("summarize", END)
        builder.add_edge("extract_analytics", END)
        builder.add_edge("compare_documents", END)
        builder.add_edge("qa_rag", END)
        builder.add_edge("qa_index", END)
        builder.add_edge("qa_ask", END)

        return builder.compile()

    def _prepare_request_node(self, state: dict) -> dict:
        state.setdefault("warnings", [])
        state.setdefault("errors", [])
        state.setdefault("metadata", {})
        state.setdefault("chat_history", [])

        state["metadata"]["graph_started"] = True

        return state

    @staticmethod
    def _route_from_prepare(state: dict) -> str:
        if state.get("user_intent") == "qa_ask":
            return "qa_ask"

        return "classify_document"

    def _classify_document_node(self, state: dict) -> dict:
        raw_text = state.get("raw_text", "")

        if not raw_text:
            state["document_type"] = "generic"
            state.setdefault("metadata", {})["document_classified"] = False
            return state

        document_type = self.classification_service.classify_document(raw_text)

        state["document_type"] = self.classification_service.validate_document_type(
            document_type
        )

        state.setdefault("metadata", {})["document_classified"] = True

        return state

    def _classify_user_intent_node(self, state: dict) -> dict:
        explicit_intent = state.get("user_intent")

        allowed_explicit_intents = {
            "summarize",
            "extract_analytics",
            "compare_documents",
            "qa_rag",
            "qa_index",
            "qa_ask",
        }

        if explicit_intent in allowed_explicit_intents:
            state["user_intent"] = explicit_intent
            state.setdefault("metadata", {})["intent_classified"] = False
            state.setdefault("metadata", {})["intent_source"] = "explicit"
            return state

        user_intent = self.classification_service.classify_user_intent(
            state.get("user_request")
        )

        state["user_intent"] = self.classification_service.validate_user_intent(
            user_intent
        )

        state.setdefault("metadata", {})["intent_classified"] = True
        state.setdefault("metadata", {})["intent_source"] = "classifier"

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
            filename=state.get("filename"),
        )

        state["analytics_result"] = result

        analytics_warnings = result.get("warnings", [])

        if analytics_warnings:
            state.setdefault("warnings", []).extend(analytics_warnings)

        state.setdefault("metadata", {}).update(
            {
                "executed_tool": "extract_analytics",
                "analytics_generated": True,
                "charts_generated": result.get("metadata", {}).get(
                    "charts_generated",
                    0,
                ),
                "metrics_detected": result.get("metadata", {}).get(
                    "metrics_detected",
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
            filename_a=state.get("filename"),
            filename_b=state.get("second_filename"),
        )

        state["comparison_result"] = result

        comparison_warnings = result.get("metadata", {}).get("warnings", [])

        if comparison_warnings:
            state.setdefault("warnings", []).extend(comparison_warnings)

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
                "qa_mode": "single_shot_rag",
            }
        )

        return state

    def _qa_index_node(self, state: dict) -> dict:
        result = self.qa_service.index_document(
            text=state.get("raw_text", ""),
            filename=state.get("filename"),
        )

        state["qa_index_result"] = result

        if not result.get("document_id"):
            state.setdefault("errors", []).append(
                result.get("message", "No se pudo indexar el documento.")
            )

        state.setdefault("metadata", {}).update(
            {
                "executed_tool": "qa_index",
                "qa_indexed": bool(result.get("document_id")),
                "document_id": result.get("document_id"),
                "chunks_indexed": result.get("chunks_indexed", 0),
            }
        )

        return state

    def _qa_ask_node(self, state: dict) -> dict:
        question = state.get("user_request") or ""
        document_id = state.get("document_id") or ""

        result = self.qa_service.answer_question_by_document_id(
            document_id=document_id,
            question=question,
        )

        state["qa_result"] = result

        state.setdefault("metadata", {}).update(
            {
                "executed_tool": "qa_ask",
                "qa_generated": True,
                "qa_mode": "indexed_chat_rag",
                "document_id": document_id,
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

        if user_intent == "qa_index":
            return "qa_index"

        if user_intent == "qa_ask":
            return "qa_ask"

        return "summarize"