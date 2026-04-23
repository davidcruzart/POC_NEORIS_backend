from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    raw_text: str
    user_request: Optional[str]
    percentage: int

    document_type: str
    user_intent: str

    summary_result: Dict[str, Any]
    analytics_result: Dict[str, Any]

    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]