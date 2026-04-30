from app.agent import Agent


class AgentService:
    def __init__(self, agent: Agent | None = None):
        self.agent = agent or Agent()

    def run_flow(self, initial_state: dict) -> dict:
        return self.agent.run(initial_state)