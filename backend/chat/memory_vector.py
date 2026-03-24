"""
memory_vector.py
────────────────
Embedding and retrieval utilities for chat_memory summary vectors.
Uses OpenAI text-embedding-3-small (1536 dims) and pgvector cosine similarity.
"""
import logging

from django.db import connection

logger = logging.getLogger(__name__)

# Lazy singleton — initialised on first call
_embeddings_model = None


def _get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        from langchain_openai import OpenAIEmbeddings
        _embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    return _embeddings_model


def embed_text(text: str):
    """Embed a single text string. Returns list[float] or None on failure."""
    try:
        model = _get_embeddings_model()
        vectors = model.embed_documents([text])
        return vectors[0]
    except Exception as e:
        logger.error("Embedding generation failed: %s", e, exc_info=True)
        return None


def _vector_to_str(vector):
    """Convert a list of floats to pgvector literal format."""
    return "[" + ",".join(str(v) for v in vector) + "]"


def save_summary_vector(memory_id: int, vector: list) -> None:
    """Store the embedding vector for a chat_memory row."""
    vector_str = _vector_to_str(vector)
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE chat_memory SET summary_vector = %s::vector WHERE memory_id = %s",
            [vector_str, memory_id],
        )


def retrieve_relevant_memories(user_id: int, query_text: str, top_k: int = 3):
    """
    Find the top-k most semantically similar past conversations for a user.

    Returns list of dicts: [{"summary": str, "ended_at": datetime, "similarity": float}]
    Returns [] on any failure.
    """
    query_vector = embed_text(query_text)
    if query_vector is None:
        return []

    vector_str = _vector_to_str(query_vector)
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT summary, ended_at,
                       1 - (summary_vector <=> %s::vector) AS similarity
                FROM chat_memory
                WHERE user_id = %s
                  AND summary_vector IS NOT NULL
                ORDER BY summary_vector <=> %s::vector
                LIMIT %s
                """,
                [vector_str, user_id, vector_str, top_k],
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error("Memory retrieval query failed: %s", e, exc_info=True)
        return []

    return [
        {"summary": row[0], "ended_at": row[1], "similarity": row[2]}
        for row in rows
    ]
