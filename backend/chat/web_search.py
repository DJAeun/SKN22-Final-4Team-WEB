"""
web_search.py
─────────────
Conditional web search for latest tech information.
Only fires when Hari's stored content doesn't cover the topic.
"""
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchDecision(BaseModel):
    needs_search: bool = Field(
        description="True if the user is asking about a tech topic that requires up-to-date factual information."
    )
    search_query: str = Field(
        default="",
        description="Optimized search query in English if needs_search is True, empty string otherwise."
    )


def should_web_search(user_input: str, content_results: list) -> tuple:
    """
    Decide whether to perform a web search.

    Skips search if generated_contents already has a good match (similarity >= 0.5).
    Otherwise, asks gpt-5.4-mini to classify the intent.

    Returns (should_search: bool, optimized_query: str).
    """
    # If Hari's own content already covers this topic well, skip search
    if content_results and any(r.get("similarity", 0) >= 0.5 for r in content_results):
        return False, ""

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(model="gpt-5.4-mini", temperature=0, timeout=5)
        structured_llm = llm.with_structured_output(SearchDecision)
        result = structured_llm.invoke([
            SystemMessage(content=(
                "You decide whether a user message needs a real-time web search for tech news or facts. "
                "Return needs_search=True ONLY for questions about specific tech topics, recent events, "
                "product specs, or news that require up-to-date information. "
                "Return needs_search=False for casual chat, personal questions, greetings, opinions, "
                "or anything that can be answered from general knowledge."
            )),
            HumanMessage(content=user_input),
        ])
        return result.needs_search, result.search_query
    except Exception as e:
        logger.error("Search decision failed: %s", e, exc_info=True)
        return False, ""


def perform_web_search(query: str, max_results: int = 3) -> list:
    """
    Perform a web search using Tavily.

    Returns list of dicts: [{"title": str, "content": str, "url": str}]
    Returns [] on any failure.
    """
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        tool = TavilySearchResults(max_results=max_results)
        results = tool.invoke(query)
        if isinstance(results, list):
            return [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                }
                for r in results
            ]
        return []
    except Exception as e:
        logger.error("Web search failed: %s", e, exc_info=True)
        return []
