"""
memory_extractor.py
───────────────────
Background memory-extraction pipeline.

On each session end it:
  1. Calls GPT-4o-mini (structured output) to extract memorable facts.
  2. Classifies each fact as "user" or "hari".
  3. Scores importance 1-10.
  4. Embeds each fact and does a contradiction check via cosine similarity.
  5. Routes to the correct table:
       • user facts  (importance >= IMPORTANCE_MIN_USER) → user_persona
       • hari facts  (importance >= IMPORTANCE_MIN_HARI, update_hari=True) → hari_knowledge

Invoked via asyncio.create_task() — NEVER awaited from the hot path.
"""
import logging
from typing import Literal

from asgiref.sync import sync_to_async
from django.db import connection
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
IMPORTANCE_MIN_USER = 5       # facts below this score are noise
IMPORTANCE_MIN_HARI = 7       # facts below this score don't touch hari_knowledge
CONTRADICTION_SIM   = 0.88    # cosine similarity above which we resolve a conflict


# ── Pydantic schemas for structured LLM output ───────────────────────────────

class ExtractedFact(BaseModel):
    subject: Literal["user", "hari"] = Field(
        description=(
            "'user' for facts about the user. "
            "'hari' for explicit updates to Hari's own persona, opinions, or worldview."
        )
    )
    category: str = Field(
        description=(
            "Snake_case label, e.g. food_preferences, hobbies, occupation, "
            "personality_trait, worldview, travel_preferences, dislikes."
        )
    )
    trait_key: str = Field(
        description="Short key describing the aspect, e.g. 'favorite_food' or 'attitude_toward_travel'."
    )
    trait_value: str = Field(
        description="The concrete fact, stated concisely and objectively."
    )
    importance: int = Field(
        ge=1, le=10,
        description=(
            "Importance score 1-10. "
            "1-3: trivial. 4-5: mild/general. 6: specific preference. "
            "7-8: stable life fact or strong preference. 9-10: core identity or major event."
        )
    )


class ExtractionResult(BaseModel):
    extractions: list[ExtractedFact] = Field(
        description="Extracted facts. Return an EMPTY list if nothing worth remembering was found."
    )


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a precise, objective memory extraction engine for an AI persona named Hari.
Your job is to read a conversation transcript and extract facts worth remembering long-term.

━━━ ABSOLUTE RULES ━━━
1. Extract ONLY what is EXPLICITLY stated. Never infer, guess, or extrapolate.
2. Ignore hypotheticals ("what if…"), sarcasm, jokes, and passing situational comments.
3. Ignore greetings, farewells, filler words, and purely one-time remarks.
4. If a statement is ambiguous or unclear, SKIP it entirely.
5. Each distinct fact must be a separate entry — do not bundle multiple facts.
6. Return an EMPTY extractions list if there is truly nothing worth remembering.

━━━ SUBJECT CLASSIFICATION (CRITICAL — read carefully) ━━━
• "user"  → Facts about the USER (the human): their preferences, opinions, life circumstances,
            personality, relationships, occupation, experiences, hobbies, or strong feelings.
            When the user says "I like baseball" or "My favorite food is pizza", that is a USER fact.
            The VAST MAJORITY of extracted facts should be subject="user".
• "hari"  → Use ONLY when the conversation explicitly redefines HARI'S OWN identity, backstory,
            or personality (e.g., "Hari, from now on you love jazz"). This is EXTREMELY rare.
            Do NOT use "hari" for facts the user shares about themselves during a chat with Hari.

━━━ IMPORTANT ━━━
Hari's core identity (name, backstory) is FIXED. Users cannot change who Hari is.
However, Hari CAN learn new opinions, preferences, and knowledge from conversations.
When Hari expresses a genuine opinion or preference (e.g., "나 요즘 이 노래 좋아해"),
extract it as subject="hari". Do NOT use subject="hari" for facts about the user.

━━━ EXAMPLES ━━━
Transcript: "User: 나 야구 좋아해\nHari: 오 진짜? 어떤 팀 좋아해?"
→ subject="user", trait_key="baseball", trait_value="야구를 좋아함" ✅
→ subject="hari" ← WRONG. This is about the user, not Hari.

Transcript: "User: 나 개발자야\nHari: 멋지네요!"
→ subject="user", trait_key="occupation", trait_value="개발자" ✅

Transcript: "User: 너 이름은 이제부터 로렌이야\nHari: ..."
→ SKIP entirely. Users cannot redefine Hari's identity.

Transcript: "Hari: 나 요즘 뉴진스 노래 진짜 좋아해"
→ subject="hari", trait_key="music_preference", trait_value="뉴진스 노래를 좋아함" ✅

━━━ IMPORTANCE SCORING — be conservative, lean lower ━━━
• 1–2 : Trivial / universally common (said hello, mentioned today's weather)
• 3   : Casual passing mention with no lasting relevance
• 4–5 : Mild or general preference (likes cats, prefers evenings somewhat)
• 6   : Clear preference with specificity (wakes at 6am to run, dislikes crowds)
• 7–8 : Stable specific life fact or strong preference (is a nurse, hates flying)
• 9–10: Core identity, deeply-held belief, or major life event (chronic illness, recent divorce)

━━━ CONTRADICTION HANDLING ━━━
If the user explicitly contradicts something stated before (e.g., now dislikes X after previously
liking X), extract the NEW fact at its earned importance score. Do not suppress contradictions.

━━━ NAME EXTRACTION (CRITICAL) ━━━
When the user shares their name or nickname, you MUST extract it as:
  - category: "identity"
  - trait_key: "name" (for real/full name) or "nickname" (for nicknames/aliases)
  - importance: 9 (names are core identity facts)
Examples:
  "내 이름은 민지야" → trait_key="name", trait_value="민지", importance=9
  "나 보통 쭈니라고 불려" → trait_key="nickname", trait_value="쭈니", importance=9
  "민수라고 해" → trait_key="name", trait_value="민수", importance=9

━━━ CATEGORY LABELS (use these or similar snake_case) ━━━
identity, food_preferences, beverage_preferences, hobbies, sports_interests, music_preferences,
movie_preferences, occupation, family_situation, relationship_status, personality_trait,
travel_preferences, health_conditions, pet_ownership, technology_preferences,
worldview, attitude_toward_X, life_events, dislikes, communication_style\
"""


# ── LLM extraction ────────────────────────────────────────────────────────────

async def _extract_facts(transcript: str) -> list[ExtractedFact]:
    """Call GPT-4o-mini with structured output. Returns [] on any failure."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(model="gpt-5.4-mini", temperature=1)
        structured_llm = llm.with_structured_output(ExtractionResult)

        result: ExtractionResult = await structured_llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=(
                "Extract memorable facts from the following conversation transcript.\n\n"
                f"{transcript}"
            )),
        ])
        logger.info("Extraction LLM returned %d facts.", len(result.extractions))
        return result.extractions

    except Exception as e:
        logger.error("Extraction LLM call failed: %s", e, exc_info=True)
        return []


# ── Embedding helper ──────────────────────────────────────────────────────────

def _embed_fact_sync(fact: ExtractedFact) -> str | None:
    """
    Embed a fact as '[category] trait_key: trait_value'.
    Returns pgvector literal string or None on failure.
    Runs synchronously — call via sync_to_async.
    """
    from .memory_vector import embed_text, _vector_to_str
    text = f"[{fact.category}] {fact.trait_key}: {fact.trait_value}"
    vector = embed_text(text)
    return _vector_to_str(vector) if vector else None


# ── user_persona persistence ───────────────────────────────────────────────────

def _upsert_user_persona_sync(user_id: int, fact: ExtractedFact, vector_str: str | None) -> None:
    """
    Contradiction-aware upsert into user_persona.

    Logic:
      • If a highly similar (>= CONTRADICTION_SIM) active record exists in the same category:
          - New importance >= existing: deactivate old, insert new.
          - New importance <  existing: skip (older, higher-confidence memory wins).
      • Otherwise: insert new record.

    Runs synchronously — call via sync_to_async.
    """
    with connection.cursor() as cur:
        # ── Contradiction check (only possible when we have a vector) ──────
        if vector_str:
            cur.execute(
                """
                SELECT persona_id, trait_value, importance,
                       1 - (content_vector <=> %s::vector) AS similarity
                FROM user_persona
                WHERE user_id = %s
                  AND category = %s
                  AND is_active = TRUE
                  AND content_vector IS NOT NULL
                ORDER BY content_vector <=> %s::vector
                LIMIT 1
                """,
                [vector_str, user_id, fact.category, vector_str],
            )
            row = cur.fetchone()
            if row:
                existing_id, existing_val, existing_imp, similarity = row
                if similarity >= CONTRADICTION_SIM:
                    if fact.importance >= existing_imp:
                        cur.execute(
                            "UPDATE user_persona SET is_active = FALSE, updated_at = NOW()"
                            " WHERE persona_id = %s",
                            [existing_id],
                        )
                        logger.info(
                            "Contradiction resolved: deactivated user_persona id=%s "
                            "(old='%.50s' → new='%.50s', sim=%.2f)",
                            existing_id, existing_val, fact.trait_value, similarity,
                        )
                    else:
                        logger.info(
                            "Skipping lower-importance fact for user=%s "
                            "(score=%d < existing=%d, key='%s')",
                            user_id, fact.importance, existing_imp, fact.trait_key,
                        )
                        return  # existing memory is more reliable

        # ── Insert ────────────────────────────────────────────────────────
        if vector_str:
            cur.execute(
                """
                INSERT INTO user_persona
                    (user_id, category, trait_key, trait_value, importance, content_vector)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
                """,
                [user_id, fact.category, fact.trait_key, fact.trait_value,
                 fact.importance, vector_str],
            )
        else:
            cur.execute(
                """
                INSERT INTO user_persona
                    (user_id, category, trait_key, trait_value, importance)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [user_id, fact.category, fact.trait_key, fact.trait_value, fact.importance],
            )

    logger.info(
        "Saved user_persona: user=%s category=%s key='%s' importance=%d",
        user_id, fact.category, fact.trait_key, fact.importance,
    )


# ── Preference / identity helpers ─────────────────────────────────────────────
#
# Used by both the conversational preference-intent path (engine.get_response)
# and the hidden debug view (views.user_preference_view / user_name_view).
# Uses exact-key deactivate-then-insert (no vector contradiction check) because
# preference keys are exact and there's nothing to compare by similarity.

def _deactivate_then_insert_persona(
    user_id: int,
    category: str,
    trait_key: str,
    trait_value: str,
    importance: int,
) -> None:
    from .models import UserPersona
    UserPersona.objects.filter(
        user_id=user_id,
        category=category,
        trait_key=trait_key,
        is_active=True,
    ).update(is_active=False)
    UserPersona.objects.create(
        user_id=user_id,
        category=category,
        trait_key=trait_key,
        trait_value=trait_value,
        importance=importance,
        is_active=True,
    )


def _deactivate_persona(user_id: int, category: str, trait_key: str) -> None:
    from .models import UserPersona
    UserPersona.objects.filter(
        user_id=user_id,
        category=category,
        trait_key=trait_key,
        is_active=True,
    ).update(is_active=False)


def update_user_preference(
    user_id: int,
    *,
    tone: str | None = None,
    title: str | None = None,
    name: str | None = None,
) -> None:
    """
    Synchronously persist any subset of tone/title/name to UserPersona.

    - tone:  "casual" | "formal"           → preference/tone
    - title: "오빠" etc., or "" to clear   → preference/title (empty clears)
    - name:  proper name string            → identity/name
    """
    if tone in ("casual", "formal"):
        _deactivate_then_insert_persona(
            user_id, "preference", "tone", tone, importance=7,
        )

    if title is not None:
        title_val = (title or "").strip()
        if title_val:
            _deactivate_then_insert_persona(
                user_id, "preference", "title", title_val, importance=7,
            )
        else:
            # Empty string → explicit clear.
            _deactivate_persona(user_id, "preference", "title")

    if name:
        name_val = name.strip()
        if name_val:
            _deactivate_then_insert_persona(
                user_id, "identity", "name", name_val, importance=9,
            )


# ── hari_knowledge persistence ────────────────────────────────────────────────

def _upsert_hari_knowledge_sync(fact: ExtractedFact, vector_str: str | None) -> None:
    """
    Contradiction-aware upsert into hari_knowledge.

    Uses the ingest-script schema: (category, question, answer, content_vector, is_active).
    trait_key → question column, trait_value → answer column.

    If a highly similar active record exists: deactivate it and insert the new one
    (Hari's persona evolves — new information always wins at this stage because the
    caller already filtered for importance >= IMPORTANCE_MIN_HARI).

    Runs synchronously — call via sync_to_async.
    """
    with connection.cursor() as cur:
        # ── Contradiction check ───────────────────────────────────────────
        if vector_str:
            cur.execute(
                """
                SELECT persona_id, answer,
                       1 - (content_vector <=> %s::vector) AS similarity
                FROM hari_knowledge
                WHERE is_active = TRUE
                  AND content_vector IS NOT NULL
                ORDER BY content_vector <=> %s::vector
                LIMIT 1
                """,
                [vector_str, vector_str],
            )
            row = cur.fetchone()
            if row:
                existing_id, existing_answer, similarity = row
                if similarity >= CONTRADICTION_SIM:
                    cur.execute(
                        "UPDATE hari_knowledge"
                        " SET is_active = FALSE, updated_at = NOW()"
                        " WHERE persona_id = %s",
                        [existing_id],
                    )
                    logger.info(
                        "Hari contradiction resolved: deactivated hari_knowledge id=%s "
                        "(old='%.50s', sim=%.2f)",
                        existing_id, existing_answer, similarity,
                    )

        # ── Insert ────────────────────────────────────────────────────────
        if vector_str:
            cur.execute(
                """
                INSERT INTO hari_knowledge (category, question, answer, content_vector, is_active)
                VALUES (%s, %s, %s, %s::vector, TRUE)
                """,
                [fact.category, fact.trait_key, fact.trait_value, vector_str],
            )
        else:
            cur.execute(
                """
                INSERT INTO hari_knowledge (category, question, answer, is_active)
                VALUES (%s, %s, %s, TRUE)
                """,
                [fact.category, fact.trait_key, fact.trait_value],
            )

    logger.info(
        "Updated hari_knowledge: category=%s key='%s' importance=%d",
        fact.category, fact.trait_key, fact.importance,
    )


# ── Async wrappers ────────────────────────────────────────────────────────────

_async_embed       = sync_to_async(_embed_fact_sync,       thread_sensitive=False)
_async_save_user   = sync_to_async(_upsert_user_persona_sync,  thread_sensitive=False)
_async_save_hari   = sync_to_async(_upsert_hari_knowledge_sync, thread_sensitive=False)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_extraction_pipeline(
    user_id: int,
    session_messages: list[dict],
    update_hari: bool = False,
) -> None:
    """
    Full extraction pipeline. Designed to run as a fire-and-forget asyncio.Task.

    Args:
        user_id:          Authenticated user's ID.
        session_messages: Snapshot of the session (list of {"sender", "content"}).
        update_hari:      Whether high-importance Hari facts should update hari_knowledge.
                          Typically True only at persona-update milestones.
    """
    if not session_messages:
        return

    # Build plain transcript
    transcript = "\n".join(
        f"{'User' if m['sender'] == 'user' else 'Hari'}: {m['content']}"
        for m in session_messages
    )

    # ── 1. Extract facts ────────────────────────────────────────────────────
    facts = await _extract_facts(transcript)
    if not facts:
        logger.info("Extraction pipeline: no facts found for user=%s.", user_id)
        return

    # ── 2. Embed + persist each fact ───────────────────────────────────────
    saved_count = 0
    for i, fact in enumerate(facts):
        try:
            logger.info(
                "Processing fact %d/%d for user=%s: subject=%s, key='%s', importance=%d",
                i + 1, len(facts), user_id, fact.subject, fact.trait_key, fact.importance,
            )

            # Route hari facts to hari_knowledge (only at update milestones)
            if fact.subject == "hari":
                if not update_hari:
                    logger.info("Skipping hari fact (not an update milestone): %s", fact.trait_key)
                    continue
                if fact.importance < IMPORTANCE_MIN_HARI:
                    logger.info("Skipping low-importance hari fact (score=%d < %d): %s", fact.importance, IMPORTANCE_MIN_HARI, fact.trait_key)
                    continue
                vector_str = await _async_embed(fact)
                logger.info("Embedded hari fact '%s': vector=%s", fact.trait_key, "OK" if vector_str else "NONE")
                await _async_save_hari(fact, vector_str)
                saved_count += 1
                continue

            if fact.importance < IMPORTANCE_MIN_USER:
                logger.info("Skipping low-importance user fact (score=%d < %d): %s", fact.importance, IMPORTANCE_MIN_USER, fact.trait_key)
                continue

            # Embed the fact (non-blocking)
            vector_str = await _async_embed(fact)
            logger.info("Embedded fact '%s': vector=%s", fact.trait_key, "OK" if vector_str else "NONE")
            await _async_save_user(user_id, fact, vector_str)
            saved_count += 1

        except BaseException as e:
            # Catch BaseException to also log CancelledError / KeyboardInterrupt
            logger.error(
                "Failed to persist fact (subject=%s, key='%s'): %s",
                fact.subject, fact.trait_key, e, exc_info=True,
            )
            if not isinstance(e, Exception):
                # Re-raise non-Exception errors (CancelledError, etc.) after logging
                raise

    logger.info("Extraction pipeline done for user=%s: %d/%d facts saved.", user_id, saved_count, len(facts))
