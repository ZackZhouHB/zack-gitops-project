"""Web search tool — DuckDuckGo search for real-time information.

Used when the internal knowledge base (Weaviate) doesn't have the answer,
or when the question requires up-to-date information from the internet.
"""

import time
import logging
from ddgs import DDGS

logger = logging.getLogger("tools.web_search")


async def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web using DuckDuckGo and return results."""
    start = time.time()

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(f"web_search: found {len(formatted)} results in {elapsed_ms}ms")

        return {
            "results": formatted,
            "count": len(formatted),
            "query": query,
            "elapsed_ms": elapsed_ms,
        }

    except Exception as e:
        logger.error(f"web_search failed: {e}")
        return {"error": str(e), "query": query, "results": [], "count": 0}
