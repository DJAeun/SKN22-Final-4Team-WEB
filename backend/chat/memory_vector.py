"""
memory_vector.py
────────────────
Embedding and retrieval utilities for chat_memory and user_persona.
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


def retrieve_relevant_memories(user_id: int, query_text: str, top_k: int = 3, query_vector=None):
    """
    Find the top-k most semantically similar past conversations for a user.

    Returns list of dicts: [{"summary": str, "ended_at": datetime, "similarity": float}]
    Returns [] on any failure.

    If query_vector is provided, skips the embedding call (for parallelization).
    """
    if query_vector is None:
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


def retrieve_hari_knowledge(query_text: str, top_k: int = 5, query_vector=None):
    """
    Find the top-k most relevant Hari persona Q&As for a given query.

    Returns list of dicts: [{"category": str, "question": str, "answer": str, "similarity": float}]
    Returns [] on any failure.

    If query_vector is provided, skips the embedding call (for parallelization).
    """
    if query_vector is None:
        query_vector = embed_text(query_text)
    if query_vector is None:
        return []

    vector_str = _vector_to_str(query_vector)
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT category, question, answer,
                       1 - (content_vector <=> %s::vector) AS similarity
                FROM hari_knowledge
                WHERE is_active = TRUE
                  AND content_vector IS NOT NULL
                ORDER BY content_vector <=> %s::vector
                LIMIT %s
                """,
                [vector_str, vector_str, top_k],
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error("Hari knowledge retrieval failed: %s", e, exc_info=True)
        return []

    return [
        {"category": row[0], "question": row[1], "answer": row[2], "similarity": row[3]}
        for row in rows
    ]


def retrieve_generated_contents(query_text: str, top_k: int = 3, min_similarity: float = 0.3, query_vector=None):
    """
    Find the top-k most relevant Hari-generated content (scripts/videos) for a query.

    Returns list of dicts with title, script_text, summary, tags, platform,
    uploaded_at, content_url, and similarity. Returns [] on any failure.

    If query_vector is provided, skips the embedding call (for parallelization).
    """
    if query_vector is None:
        query_vector = embed_text(query_text)
    if query_vector is None:
        return []

    vector_str = _vector_to_str(query_vector)
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT title, script_text, summary, tags, platform,
                       uploaded_at, content_url,
                       1 - (content_vector <=> %s::vector) AS similarity
                FROM generated_contents
                WHERE is_published = TRUE
                  AND content_vector IS NOT NULL
                  AND 1 - (content_vector <=> %s::vector) >= %s
                ORDER BY content_vector <=> %s::vector
                LIMIT %s
                """,
                [vector_str, vector_str, min_similarity, vector_str, top_k],
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error("Generated contents retrieval failed: %s", e, exc_info=True)
        return []

    return [
        {
            "title": row[0],
            "script_text": row[1],
            "summary": row[2],
            "tags": row[3],
            "platform": row[4],
            "uploaded_at": row[5],
            "content_url": row[6],
            "similarity": row[7],
        }
        for row in rows
    ]


def embed_and_save_content_vector(content_id: int, script_text: str, summary: str = "") -> None:
    """Embed script+summary and store the vector in generated_contents."""
    text_to_embed = f"{summary}\n{script_text}" if summary else script_text
    vector = embed_text(text_to_embed)
    if vector is None:
        logger.error("Failed to embed content %d", content_id)
        return
    vector_str = _vector_to_str(vector)
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE generated_contents SET content_vector = %s::vector WHERE content_id = %s",
            [vector_str, content_id],
        )


def _summarize_script(script_text: str) -> str:
    """Summarize a video script into 1-2 sentences in Korean via LLM."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatOpenAI(model="gpt-5.4-mini", temperature=0.3, timeout=15)
    result = llm.invoke([
        SystemMessage(content=(
            "You summarize video scripts into 1-2 concise sentences in Korean. "
            "Focus on the main topic and key points. No markdown, no bullet points."
        )),
        HumanMessage(content=script_text),
    ])
    return result.content.strip()


def process_new_contents() -> int:
    """
    Find generated_contents rows missing summary or content_vector,
    auto-generate them, and return the number of rows processed.
    """
    with connection.cursor() as cur:
        cur.execute(
            "SELECT content_id, script_text, summary FROM generated_contents "
            "WHERE summary IS NULL OR content_vector IS NULL"
        )
        rows = cur.fetchall()

    processed = 0
    for content_id, script_text, summary in rows:
        try:
            # Step 1: Summarize if missing
            if not summary:
                summary = _summarize_script(script_text)
                with connection.cursor() as cur:
                    cur.execute(
                        "UPDATE generated_contents SET summary = %s WHERE content_id = %s",
                        [summary, content_id],
                    )
                logger.info("Summarized content %d", content_id)

            # Step 2: Embed and save vector
            embed_and_save_content_vector(content_id, script_text, summary)
            logger.info("Embedded content %d", content_id)
            processed += 1
        except Exception as e:
            logger.error("Failed to process content %d: %s", content_id, e, exc_info=True)

    return processed


def retrieve_user_persona(user_id: int):
    """
    Fetch all active facts about a user from user_persona.

    Returns list of dicts: [{"category": str, "trait_key": str, "trait_value": str, "importance": int}]
    Returns [] on any failure.
    """
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT category, trait_key, trait_value, importance
                FROM user_persona
                WHERE user_id = %s
                  AND is_active = TRUE
                ORDER BY importance DESC
                """,
                [user_id],
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error("User persona retrieval failed: %s", e, exc_info=True)
        return []

    return [
        {"category": row[0], "trait_key": row[1], "trait_value": row[2], "importance": row[3]}
        for row in rows
    ]
