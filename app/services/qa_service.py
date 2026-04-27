from typing import Any

import numpy as np
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE, DEFAULT_MODEL_NAME


class QAService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=DEFAULT_MODEL_NAME,
            temperature=0,
        )

        self.embeddings = OpenAIEmbeddings()

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

    def answer_question(
        self,
        text: str,
        question: str,
        top_k: int = 4,
    ) -> dict[str, Any]:
        chunks = self.splitter.split_text(text)

        if not chunks:
            return {
                "question": question,
                "answer": "No se ha podido generar una respuesta porque el documento no contiene texto útil.",
                "retrieved_chunks": [],
                "metadata": {
                    "chunks_generated": 0,
                    "top_k": top_k,
                },
            }

        retrieved_chunks = self._retrieve_relevant_chunks(
            chunks=chunks,
            question=question,
            top_k=top_k,
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
                "chunks_generated": len(chunks),
                "chunks_used": len(retrieved_chunks),
                "top_k": top_k,
                "retrieval": "in_memory_embedding_cosine_similarity",
            },
        }

    def _retrieve_relevant_chunks(
        self,
        chunks: list[str],
        question: str,
        top_k: int,
    ) -> list[str]:
        document_vectors = self.embeddings.embed_documents(chunks)
        question_vector = self.embeddings.embed_query(question)

        question_array = np.array(question_vector, dtype=float)
        document_array = np.array(document_vectors, dtype=float)

        scores = self._cosine_similarity(
            matrix=document_array,
            vector=question_array,
        )

        top_indices = np.argsort(scores)[::-1][:top_k]

        return [chunks[index] for index in top_indices]

    @staticmethod
    def _cosine_similarity(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
        matrix_norm = np.linalg.norm(matrix, axis=1)
        vector_norm = np.linalg.norm(vector)

        denominator = matrix_norm * vector_norm

        denominator = np.where(denominator == 0, 1e-10, denominator)

        return np.dot(matrix, vector) / denominator

    def _generate_answer(
        self,
        question: str,
        retrieved_chunks: list[str],
    ) -> str:
        context = "\n\n---\n\n".join(retrieved_chunks)

        prompt = f"""
Responde a la pregunta usando únicamente el contexto recuperado del documento.

Reglas:
- No inventes información.
- Si el contexto no contiene la respuesta, dilo claramente.
- Responde de forma clara y directa.
- Si hay cifras, respétalas exactamente.

Pregunta:
{question}

Contexto:
{context}
"""

        response = self.llm.invoke(prompt)
        return str(response.content).strip()