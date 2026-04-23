def route_by_intent(state: dict) -> str:
    user_intent = state.get("user_intent", "summarize")

    if user_intent == "extract_analytics":
        return "extract_analytics"

    return "summarize"