from app.agent import Agent
from app.implementations.summarizers.openai_summarizer import OpenAISummarizer
from app.services.analytics_service import AnalyticsService
from app.services.classification_service import ClassificationService
from app.services.comparison_service import ComparisonService
from app.services.qa_service import QAService
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
        comparison_service = ComparisonService()
        qa_service = QAService()

        self.agent = Agent(
            summary_service=summary_service,
            classification_service=classification_service,
            analytics_service=analytics_service,
            comparison_service=comparison_service,
            qa_service=qa_service,
        )

    def run_flow(self, initial_state: dict) -> dict:
        return self.agent.run(initial_state)