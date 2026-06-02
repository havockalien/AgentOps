"""
AgentOps — Web Search Tool
===========================
Sends a search query to a search API (SerpAPI or stub) and returns
structured results. Falls back to an in-memory stub when no API key is set.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from agent.tools.base_tool import BaseTool, get_registry

log = logging.getLogger("agentops.tools.web_search")


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for information. Use for real-time data, news, "
        "documentation, or any question requiring up-to-date information."
    )
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (1-10).",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        num_results: int = int(kwargs.get("num_results", 5))
        serpapi_key = os.getenv("SERPAPI_KEY")

        if not serpapi_key:
            # Stub response for dev/test
            log.warning("SERPAPI_KEY not set — returning stub search results.")
            return {
                "output": (
                    f"[STUB] Search results for: '{query}'\n"
                    "1. Result 1: AgentOps documentation — agentops.ai\n"
                    "2. Result 2: LangGraph tutorial — langchain.com/langgraph\n"
                    "3. Result 3: OpenAI API reference — platform.openai.com"
                ),
                "results": [
                    {
                        "title": f"Stub result {i}",
                        "url": f"https://example.com/{i}",
                        "snippet": f"Result {i} for {query}",
                    }
                    for i in range(1, min(num_results, 3) + 1)
                ],
                "stub": True,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={"q": query, "num": num_results, "api_key": serpapi_key},
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("organic_results", [])[:num_results]
        formatted = "\n".join(
            f"{i+1}. {r.get('title', 'N/A')}: {r.get('snippet', '')} ({r.get('link', '')})"
            for i, r in enumerate(results)
        )
        return {"output": formatted, "results": results}


# Auto-register
get_registry().register(WebSearchTool())
