"""Optional anonymous Parallel Search MCP tools for the synchronous agent loop."""

import asyncio

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ENDPOINT = "https://search.parallel.ai/mcp"
USER_AGENT = "sky-agent/0.1 (https://github.com/arteemg/sky-agent)"
TIMEOUT = 60


async def _call(name: str, arguments: dict) -> str:
    # A fresh session per call keeps concurrent chats and event loops independent.
    async with (
        asyncio.timeout(TIMEOUT),
        httpx2.AsyncClient(
            headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT,
        ) as client,
        streamable_http_client(ENDPOINT, http_client=client) as streams,
        ClientSession(*streams) as session,
    ):
        await session.initialize()
        result = await session.call_tool(name, arguments)
        text = "\n".join(
            block.text for block in result.content if block.type == "text"
        )
        if result.is_error:
            raise ValueError(text or "Parallel Search MCP returned an error.")
        return text or "No text returned by Parallel Search MCP."


def _execute(name: str, arguments: dict) -> str:
    try:
        return asyncio.run(_call(name, arguments))
    except TimeoutError:
        raise ValueError(f"Parallel Search MCP timed out after {TIMEOUT} seconds.") from None
    except ExceptionGroup as group:
        # Transport context managers wrap failures; retain the useful error text.
        def messages(exc):
            if isinstance(exc, BaseExceptionGroup):
                return [text for child in exc.exceptions for text in messages(child)]
            return [str(exc)]
        raise ValueError("; ".join(messages(group))) from None


def web_search(objective: str, search_queries: list[str], **context) -> str:
    return _execute("web_search", {
        "objective": objective, "search_queries": search_queries, **context,
    })


def web_fetch(urls: list[str], objective: str | None = None, **context) -> str:
    return _execute("web_fetch", {
        "urls": urls, "objective": objective, **context,
    })


TOOLS = {
    "web_search": {
        "function": web_search,
        "definition": {
            "name": "web_search",
            "description": "Search the web for current information and source URLs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "objective": {"type": "string", "description": "Information to find."},
                    "search_queries": {
                        "type": "array", "items": {"type": "string"}, "minItems": 1,
                        "description": "Related keyword queries of 3–6 words each.",
                    },
                },
                "required": ["objective", "search_queries"],
                "additionalProperties": False,
            },
        },
    },
    "web_fetch": {
        "function": web_fetch,
        "definition": {
            "name": "web_fetch",
            "description": "Read web pages as markdown excerpts, using known or searched URLs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array", "items": {"type": "string"},
                        "minItems": 1, "maxItems": 20,
                        "description": "HTTP or HTTPS URLs to read.",
                    },
                    "objective": {
                        "type": "string", "maxLength": 200,
                        "description": "Information to extract from the pages.",
                    },
                },
                "required": ["urls"],
                "additionalProperties": False,
            },
        },
    },
}
