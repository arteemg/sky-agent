"""The agent brain: one function in, one reply out.

respond(chat_id, text, config) -> str

Speaks the OpenAI Chat Completions format — the lingua franca that
nearly every LLM provider supports: OpenAI, Anthropic, OpenRouter,
Groq, Mistral, Together, DeepSeek, and local runtimes like Ollama.
Point provider_base_url in agent.yaml at your provider, set
LLM-API-KEY, and everything else stays the same.
"""

import json
import os
import uuid

from openai import OpenAI

from agent import memory, tools

DEFAULT_BASE_URL = "https://api.anthropic.com/v1/"  # Anthropic's OpenAI-compatible endpoint

_client = None
_client_base = None


def _get_client(config: dict) -> OpenAI:
    """One cached client; rebuilt if the base URL in config changes."""
    global _client, _client_base
    base = config.get("provider_base_url", DEFAULT_BASE_URL)
    if _client is None or _client_base != base:
        key = (
            os.environ.get("LLM-API-KEY")
            or os.environ.get("LLM_API_KEY")         # underscore variant (shells can't export hyphens)
            or os.environ.get("OPENAI_API_KEY")      # legacy name, still works
            or "no-key-needed"                       # local providers (Ollama) don't check
        )
        _client = OpenAI(base_url=base, api_key=key)
        _client_base = base
    return _client


def _openai_tools() -> list:
    """Translate our tool registry into OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": d["name"],
                "description": d["description"],
                "parameters": d.get("input_schema") or {"type": "object", "properties": {}},
            },
        }
        for d in tools.DEFINITIONS
    ]


def _sanitize(history: list) -> list:
    """Merge consecutive same-role messages and drop leading non-user
    turns, so any provider gets a clean alternating history."""
    clean = []
    for msg in history:
        if not msg.get("content"):
            continue
        if clean and clean[-1]["role"] == msg["role"]:
            clean[-1]["content"] += "\n" + msg["content"]
        else:
            clean.append(dict(msg))
    while clean and clean[0]["role"] != "user":
        clean.pop(0)
    return clean


def respond(chat_id: str, text: str, config: dict) -> str:
    """Run one turn of the agent for a given chat."""
    memory.add(chat_id, "user", text)

    history = memory.history(chat_id, limit=config.get("max_context_messages", 30))
    messages = [
        {"role": "system", "content": config.get("system_prompt", "You are a helpful assistant.")}
    ] + _sanitize(history)

    client = _get_client(config)
    kwargs = {
        "model": config.get("model", "claude-sonnet-4-6"),
        "max_tokens": config.get("max_tokens", 1024),
        "messages": messages,
    }
    tool_defs = _openai_tools()
    if tool_defs:
        kwargs["tools"] = tool_defs

    response = client.chat.completions.create(**kwargs)
    msg = response.choices[0].message

    # Tool loop: keep going until the model stops requesting tools.
    for _ in range(10):  # hard cap so a confused model can't loop forever
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            break
        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except ValueError:
                args = {}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tools.run(
                        tc.function.name, args,
                        session_id=uuid.uuid5(uuid.NAMESPACE_URL, "sky-agent:" + chat_id).hex,
                        model_name=kwargs["model"],
                    ),
                }
            )
        kwargs["messages"] = messages
        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

    reply = (msg.content or "").strip() or "(no reply)"
    memory.add(chat_id, "assistant", reply)
    return reply
