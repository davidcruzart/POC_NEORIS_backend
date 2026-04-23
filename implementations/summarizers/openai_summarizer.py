import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_TEMPERATURE,
    LARGE_DOCUMENT_BATCH_SIZE,
    MAX_FRAGMENTS,
    MAX_SUMMARY_WORKERS,
    MAX_TEXT_LENGTH_CHARS,
)
from app.core.exceptions import EmptyExtractedTextError, TextTooLargeError, TooManyFragmentsError
from app.interfaces.summarizer import Summarizer
from app.prompts.summary_prompts import (
    DIRECT_SUMMARY_PROMPT,
    FINAL_SUMMARY_PROMPT,
    PARTIAL_SUMMARY_PROMPT,
)


logger = logging.getLogger(__name__)


class OpenAISummarizer(Summarizer):
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=DEFAULT_MODEL_TEMPERATURE,
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        self.prompt_direct = ChatPromptTemplate.from_template(DIRECT_SUMMARY_PROMPT)
        self.prompt_partial = ChatPromptTemplate.from_template(PARTIAL_SUMMARY_PROMPT)
        self.prompt_final = ChatPromptTemplate.from_template(FINAL_SUMMARY_PROMPT)

    def summarize(self, text: str, target_words: int) -> str:
        self._validate_input_size(text)

        fragments = self.splitter.split_text(text)
        fragments_count = len(fragments)

        logger.info("Texto recibido para resumir.")
        logger.info("Caracteres del texto: %s", len(text))
        logger.info("Palabras objetivo: %s", target_words)
        logger.info("Número de fragmentos generados: %s", fragments_count)

        if fragments_count > MAX_FRAGMENTS:
            logger.warning(
                "Documento rechazado por exceso de fragmentos: %s > %s",
                fragments_count,
                MAX_FRAGMENTS,
            )
            raise TooManyFragmentsError(
                f"El documento genera demasiados fragmentos ({fragments_count}). "
                f"Máximo permitido: {MAX_FRAGMENTS}."
            )

        if fragments_count == 1:
            logger.info("Estrategia usada: DIRECT")
            return self._summarize_direct(text, target_words)

        if fragments_count <= 6:
            logger.info("Estrategia usada: MEDIUM_SERIAL")
            return self._summarize_medium(fragments, target_words)

        logger.info("Estrategia usada: LARGE_BATCHED_CONCURRENT")
        return self._summarize_large(fragments, target_words)

    @staticmethod
    def _validate_input_size(text: str) -> None:
        if not text or not text.strip():
            raise EmptyExtractedTextError("El texto extraído está vacío.")

        if len(text) > MAX_TEXT_LENGTH_CHARS:
            raise TextTooLargeError(
                f"El texto extraído es demasiado grande ({len(text)} caracteres). "
                f"Máximo permitido: {MAX_TEXT_LENGTH_CHARS}."
            )

    def _summarize_direct(self, text: str, target_words: int) -> str:
        chain = self.prompt_direct | self.llm
        response = chain.invoke({
            "texto": text,
            "palabras_objetivo": target_words,
        })
        return response.content.strip()

    def _summarize_medium(self, fragments: list[str], target_words: int) -> str:
        partial_chain = self.prompt_partial | self.llm
        final_chain = self.prompt_final | self.llm

        partial_summaries = []
        words_per_fragment = max(100, target_words // len(fragments))

        logger.info("Fragmentos a resumir en serie: %s", len(fragments))
        logger.info("Palabras objetivo por fragmento: %s", words_per_fragment)

        for index, fragment in enumerate(fragments, start=1):
            logger.info("Resumiendo fragmento %s/%s", index, len(fragments))
            response = partial_chain.invoke({
                "texto": fragment,
                "palabras_objetivo": words_per_fragment,
            })
            partial_summaries.append(response.content.strip())

        intermediate_text = "\n\n".join(partial_summaries)
        response = final_chain.invoke({
            "texto": intermediate_text,
            "palabras_objetivo": target_words,
        })

        return response.content.strip()

    @staticmethod
    def _group_fragments(fragments: list[str], batch_size: int = LARGE_DOCUMENT_BATCH_SIZE) -> list[str]:
        grouped_fragments = []

        for index in range(0, len(fragments), batch_size):
            batch = fragments[index:index + batch_size]
            grouped_fragments.append("\n\n".join(batch))

        return grouped_fragments

    def _summarize_block(self, block: str, target_words: int) -> str:
        partial_chain = self.prompt_partial | self.llm
        response = partial_chain.invoke({
            "texto": block,
            "palabras_objetivo": target_words,
        })
        return response.content.strip()

    def _summarize_large(self, fragments: list[str], target_words: int) -> str:
        batches = self._group_fragments(fragments, batch_size=LARGE_DOCUMENT_BATCH_SIZE)
        partial_summaries = [None] * len(batches)

        words_per_batch = max(120, target_words // len(batches))
        max_workers = min(MAX_SUMMARY_WORKERS, len(batches))

        logger.info("Bloques generados: %s", len(batches))
        logger.info("Palabras objetivo por bloque: %s", words_per_batch)
        logger.info("Workers concurrentes usados: %s", max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self._summarize_block, batch, words_per_batch): index
                for index, batch in enumerate(batches)
            }

            for future in as_completed(future_to_index):
                index = future_to_index[future]
                partial_summaries[index] = future.result()
                logger.info("Bloque resumido: %s/%s", index + 1, len(batches))

        intermediate_text = "\n\n".join(partial_summaries)

        final_chain = self.prompt_final | self.llm
        response = final_chain.invoke({
            "texto": intermediate_text,
            "palabras_objetivo": target_words,
        })

        return response.content.strip()