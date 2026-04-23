from app.agent.graph import build_agent_graph


class AgentService:
    def __init__(self, graph=None):
        self.graph = graph or build_agent_graph()

    def run_flow(self, initial_state: dict) -> dict:
        return self.graph.invoke(initial_state)