from app.config import MAX_TARGET_WORDS, MAX_SUMMARY_PERCENTAGE, MIN_SUMMARY_PERCENTAGE
from app.exceptions import InvalidPercentageError
from app.interfaces.summarizer import Summarizer


class SummaryService:
    def __init__(self, summarizer: Summarizer):
        self.summarizer = summarizer

    @staticmethod
    def count_words(text: str) -> int:
        return len(text.split())

    @staticmethod
    def calculate_target_words(text: str, percentage: int) -> tuple[int, int, bool]:
        if percentage < MIN_SUMMARY_PERCENTAGE or percentage > MAX_SUMMARY_PERCENTAGE:
            raise InvalidPercentageError(
                f"El porcentaje debe estar entre {MIN_SUMMARY_PERCENTAGE} y {MAX_SUMMARY_PERCENTAGE}."
            )

        original_words = len(text.split())
        calculated_target = int(original_words * (percentage / 100))

        target_words = max(50, calculated_target)
        was_capped = target_words > MAX_TARGET_WORDS
        target_words = min(target_words, MAX_TARGET_WORDS)

        return original_words, target_words, was_capped

    def summarize_text(self, text: str, percentage: int) -> dict:
        original_words, target_words, was_capped = self.calculate_target_words(text, percentage)
        summary = self.summarizer.summarize(text, target_words)
        summary_words = self.count_words(summary)

        return {
            "summary": summary,
            "summary_words": summary_words,
            "original_words": original_words,
            "target_words": target_words,
            "was_capped": was_capped,
            "max_target_words": MAX_TARGET_WORDS,
        }