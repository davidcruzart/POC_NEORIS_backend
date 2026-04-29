from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import DEFAULT_MODEL_NAME, DEFAULT_MODEL_TEMPERATURE
from app.config import DOCUMENT_TYPES, USER_INTENTS
from app.prompts.classification_prompts import (
    DOCUMENT_CLASSIFICATION_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
)


class ClassificationService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        )

        self.document_prompt = ChatPromptTemplate.from_template(
            DOCUMENT_CLASSIFICATION_PROMPT
        )
        self.intent_prompt = ChatPromptTemplate.from_template(
            INTENT_CLASSIFICATION_PROMPT
        )

    def classify_document(self, text: str) -> str:
        document_excerpt = self._build_document_excerpt(text)

        chain = self.document_prompt | self.llm
        response = chain.invoke({"texto": document_excerpt})

        label = self._normalize_label(response.content)
        return self.validate_document_type(label)

    def classify_user_intent(self, user_request: str | None = None) -> str:
        normalized_request = (user_request or "Resume este documento").strip()

        chain = self.intent_prompt | self.llm
        response = chain.invoke({"user_request": normalized_request})

        label = self._normalize_label(response.content)
        return self.validate_user_intent(label)

    @staticmethod
    def validate_document_type(document_type: str) -> str:
        if document_type not in DOCUMENT_TYPES:
            return "generic"
        return document_type

    @staticmethod
    def validate_user_intent(user_intent: str) -> str:
        if user_intent not in USER_INTENTS:
            return "summarize"
        return user_intent

    @staticmethod
    def _normalize_label(value: str) -> str:
        if not value:
            return ""

        return (
            value.strip()
            .lower()
            .replace("`", "")
            .replace('"', "")
            .replace("'", "")
            .splitlines()[0]
            .strip()
        )

    @staticmethod
    def _build_document_excerpt(text: str, max_chars: int = 12000) -> str:
        clean_text = (text or "").strip()

        if len(clean_text) <= max_chars:
            return clean_text

        head_size = max_chars // 2
        tail_size = max_chars - head_size

        head = clean_text[:head_size]
        tail = clean_text[-tail_size:]

        return (
            f"{head}\n\n"
            "[... CONTENIDO INTERMEDIO OMITIDO PARA CLASIFICACIÓN ...]\n\n"
            f"{tail}"
        )