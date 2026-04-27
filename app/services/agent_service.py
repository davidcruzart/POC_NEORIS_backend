from app.agent import Agent
from app.implementations.summarizers.openai_summarizer import OpenAISummarizer
from app.services.analytics_service import AnalyticsService
from app.services.classification_service import ClassificationService
from app.services.summary_service import SummaryService


class AgentService:
    def __init__(self, agent: Agent | None = None):
        if agent is not None:
            self.agent = agent
            return

        summarizer = OpenAISummarizer()
        summary_service = SummaryService(summarizer=summarizer)
        classification_service = ClassificationService()
        analytics_service = AnalyticsService()

        self.agent = Agent(
            summary_service=summary_service,
            classification_service=classification_service,
            analytics_service=analytics_service,
        )

    def run_flow(self, initial_state: dict) -> dict:
        return self.agent.run(initial_state)