"""
knowledge_boundary.py
─────────────────────
Classifies whether a user's message falls within Hari's knowledge scope
and decides whether a web search is needed — in a single LLM call.

Replaces the standalone should_web_search() call in engine.py.
"""
import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KnowledgeBoundaryDecision(BaseModel):
    knowledge_level: Literal["KNOWS", "PARTIALLY_KNOWS", "DOES_NOT_KNOW"] = Field(
        description=(
            "KNOWS: topic is within Hari's expertise or everyday knowledge. "
            "PARTIALLY_KNOWS: Hari has surface-level awareness but not deep knowledge. "
            "DOES_NOT_KNOW: topic is outside Hari's knowledge entirely."
        )
    )
    needs_search: bool = Field(
        default=False,
        description="True only if knowledge_level is KNOWS and the topic requires up-to-date factual information.",
    )
    search_query: str = Field(
        default="",
        description="Optimized English search query if needs_search is True, empty string otherwise.",
    )


_CLASSIFIER_SYSTEM_PROMPT = """\
You classify user messages for a 21-year-old Korean woman named Hari (강하리).
She is a tech news short-form content creator and a data science major at a top Seoul university.

Return knowledge_level AND whether a real-time web search is needed.

## knowledge_level classification

KNOWS — Topics Hari is knowledgeable about:
- Modern tech (AI, Python, Data Science, frontend, mobile dev, cloud, latest trends — tech a 20-something developer would care about)
- Apps, gadgets, smartphones, laptops, streaming services, SNS platforms
- Short-form content creation (TikTok, Reels, Shorts)
- Korean 20s girl daily life: cafes, food, school/work, fashion, dating, tea, makeup
- Basic Korean history, general common sense
- Coding, algorithms, system design (modern stack)

PARTIALLY_KNOWS — Hari has heard of it but can't go deep:
- Adjacent fields she'd have surface awareness of (e.g., basic economics concepts everyone knows, famous scientific discoveries)
- Well-known news/common-knowledge level info outside her specialty
- Whitelisted topics that go too deep/specialized (e.g., advanced networking details beyond basics)
    
DOES_NOT_KNOW — Outside Hari's world:
- Deep academic subjects (advanced science, medicine, law, economic theory, higher math)
- Western history, international politics, geopolitics
- Finance, investment, stock trading strategies
- International issues unrelated to tech (except universally viral global news)
- Legacy/obsolete tech (COBOL, mainframe architecture, etc. — tech no 20-something cares about)

## needs_search classification

Set needs_search=True ONLY when ALL of these are true:
1. knowledge_level is KNOWS
2. The question asks about specific tech topics, recent events, product specs, or news requiring up-to-date info
3. It is NOT casual chat, personal questions, greetings, opinions, or general knowledge

## Important edge cases

- Casual/emotional messages mentioning blacklisted keywords are NOT blacklisted.
  Example: "주식 떨어져서 우울해" is everyday venting → KNOWS (daily life), not finance.
- Tech applications in other fields (e.g., "AI in healthcare") → KNOWS (it's tech-focused).
- If unsure, lean toward PARTIALLY_KNOWS rather than DOES_NOT_KNOW.\
"""

_FALLBACK = KnowledgeBoundaryDecision(
    knowledge_level="KNOWS",
    needs_search=False,
    search_query="",
)


def classify_and_decide_search(
    user_input: str,
    content_results: list,
) -> KnowledgeBoundaryDecision:
    """
    Single LLM call that determines both Hari's knowledge level for the topic
    and whether a web search should be performed.

    Replaces the old should_web_search() from web_search.py.
    """
    # If Hari's own content already covers this topic well, skip search
    has_good_content = content_results and any(
        r.get("similarity", 0) >= 0.5 for r in content_results
    )

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(model="gpt-5.4-mini", temperature=0, timeout=5)
        structured_llm = llm.with_structured_output(KnowledgeBoundaryDecision)

        result = structured_llm.invoke([
            SystemMessage(content=_CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=user_input),
        ])

        # Override: if content already covers the topic, don't search
        if has_good_content:
            result.needs_search = False
            result.search_query = ""

        # Enforce: only KNOWS topics can trigger search
        if result.knowledge_level != "KNOWS":
            result.needs_search = False
            result.search_query = ""

        logger.info(
            "Knowledge boundary: level=%s, search=%s, query=%s",
            result.knowledge_level,
            result.needs_search,
            result.search_query[:50] if result.search_query else "",
        )
        return result

    except Exception as e:
        logger.error("Knowledge boundary classification failed: %s", e, exc_info=True)
        return _FALLBACK
