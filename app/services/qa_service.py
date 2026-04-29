import hashlib
import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer

from app.config import DEFAULT_MODEL_NAME
from app.prompts.qa_prompts import QA_RAG_PROMPT

logger = logging.getLogger(__name__)


class QAService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        )

        self.embedding_model_name = "sentence-transformers/all-mpnet-base-v2"
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        self.prompt = ChatPromptTemplate.from_template(QA_RAG_PROMPT)

        self.chunk_size = 1200
        self.chunk_overlap = 200
        self.top_k = 5

        self.persist_dir = Path("chroma_db")
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_dir)
        )

    def index_document(
        self,
        text: str,
        filename: str | None = None,
    ) -> dict[str, Any]:
        text = str(text or "").strip()

        if not text:
            return {
                "document_id": None,
                "filename": filename,
                "chunks_total": 0,
                "chunks_indexed": 0,
                "already_indexed": False,
                "status": "empty",
                "message": "No hay texto útil para indexar.",
            }

        document_id = self._build_document_id(text)
        chunks = self._split_text(text)

        if not chunks:
            return {
                "document_id": document_id,
                "filename": filename,
                "chunks_total": 0,
                "chunks_indexed": 0,
                "already_indexed": False,
                "status": "empty",
                "message": "No se pudieron generar chunks útiles.",
            }

        collection = self._get_or_create_collection(document_id)
        already_indexed = collection.count() > 0

        if not already_indexed:
            self._index_document(
                collection=collection,
                chunks=chunks,
                document_id=document_id,
                filename=filename,
            )

        return {
            "document_id": document_id,
            "filename": filename,
            "chunks_total": len(chunks),
            "chunks_indexed": collection.count(),
            "already_indexed": already_indexed,
            "status": "indexed",
            "metadata": {
                "method": "chroma_local_huggingface_rag",
                "embedding_model": self.embedding_model_name,
                "vector_store": "chromadb_persistent",
                "persist_dir": str(self.persist_dir),
            },
        }

    def answer_question_by_document_id(
        self,
        document_id: str,
        question: str,
    ) -> dict[str, Any]:
        document_id = str(document_id or "").strip()
        question = str(question or "").strip()

        if not document_id:
            return self._empty_result(
                question=question,
                answer="No se ha proporcionado un identificador de documento.",
            )

        if not question:
            return self._empty_result(
                question=question,
                answer="No se ha proporcionado ninguna pregunta.",
            )

        try:
            collection = self.chroma_client.get_collection(name=document_id)
        except Exception:
            return self._empty_result(
                question=question,
                answer="El documento no está indexado o no existe en la base vectorial.",
            )

        retrieved_chunks = self._retrieve_relevant_chunks(
            collection=collection,
            question=question,
        )

        answer = self._generate_answer(
            question=question,
            retrieved_chunks=retrieved_chunks,
        )

        return {
            "question": question,
            "answer": answer,
            "retrieved_chunks": retrieved_chunks,
            "metadata": {
                "method": "chroma_local_huggingface_rag",
                "embedding_model": self.embedding_model_name,
                "vector_store": "chromadb_persistent",
                "document_id": document_id,
                "chunks_indexed": collection.count(),
                "chunks_used": len(retrieved_chunks),
                "top_k": self.top_k,
            },
        }

    def answer_question(self, text: str, question: str) -> dict[str, Any]:
        index_result = self.index_document(text=text)
        document_id = index_result.get("document_id")

        if not document_id:
            return self._empty_result(
                question=question,
                answer="No se pudo indexar el documento para responder.",
            )

        return self.answer_question_by_document_id(
            document_id=document_id,
            question=question,
        )

    def _get_or_create_collection(self, document_id: str) -> Collection:
        return self.chroma_client.get_or_create_collection(
            name=document_id,
            metadata={
                "description": "Documento indexado para QA-RAG",
                "embedding_model": self.embedding_model_name,
            },
        )

    def _index_document(
        self,
        collection: Collection,
        chunks: list[str],
        document_id: str,
        filename: str | None = None,
    ) -> None:
        logger.info(
            "Indexando documento en ChromaDB. document_id=%s chunks=%s",
            document_id,
            len(chunks),
        )

        embeddings = self.embedding_model.encode(
            chunks,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

        ids = [
            f"{document_id}_chunk_{index}"
            for index in range(len(chunks))
        ]

        metadatas = [
            {
                "document_id": document_id,
                "filename": filename or "",
                "chunk_index": index,
            }
            for index in range(len(chunks))
        ]

        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def _retrieve_relevant_chunks(
        self,
        collection: Collection,
        question: str,
    ) -> list[str]:
        try:
            question_embedding = self.embedding_model.encode(
                [question],
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).tolist()[0]

            result = collection.query(
                query_embeddings=[question_embedding],
                n_results=self.top_k,
                include=["documents", "distances", "metadatas"],
            )

            documents = result.get("documents") or []

            if not documents or not documents[0]:
                return []

            return [
                str(chunk)
                for chunk in documents[0]
                if str(chunk).strip()
            ]

        except Exception as exc:
            logger.error("Error recuperando chunks desde ChromaDB: %s", exc)
            return []

    def _generate_answer(
        self,
        question: str,
        retrieved_chunks: list[str],
    ) -> str:
        if not retrieved_chunks:
            return "No he encontrado fragmentos relevantes en el documento para responder."

        context = "\n\n---\n\n".join(retrieved_chunks)
        chain = self.prompt | self.llm

        try:
            response = chain.invoke(
                {
                    "question": question,
                    "context": context,
                }
            )

            return str(response.content).strip()

        except Exception as exc:
            logger.error("Error generando respuesta QA-RAG: %s", exc)
            return "No se pudo generar la respuesta por un error interno."

    def _split_text(self, text: str) -> list[str]:
        cleaned = " ".join(text.split())

        if not cleaned:
            return []

        chunks = []
        start = 0
        text_length = len(cleaned)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk = cleaned[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            start = max(0, end - self.chunk_overlap)

        return chunks

    @staticmethod
    def _build_document_id(text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"doc_{digest[:32]}"

    @staticmethod
    def _empty_result(question: str, answer: str) -> dict[str, Any]:
        return {
            "question": question,
            "answer": answer,
            "retrieved_chunks": [],
            "metadata": {
                "method": "chroma_local_huggingface_rag",
                "chunks_used": 0,
                "vector_store": "chromadb_persistent",
            },
        }