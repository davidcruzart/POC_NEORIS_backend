from pydantic import BaseModel


class SummaryResponse(BaseModel):
    summary: str
    summary_words: int
    original_words: int
    target_words: int
    was_capped: bool
    max_target_words: int