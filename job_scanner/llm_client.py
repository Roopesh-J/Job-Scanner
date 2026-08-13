import os
from typing import Any

import anthropic

DEFAULT_MODEL = "claude-sonnet-5"

# Ceiling on pause_turn retries in call_tool_with_search. Deliberately not derived from
# max_searches — pause_turn can occur for reasons other than a search (e.g. multiple
# server-side turns before the final answer), so tying the two together can cut off a
# well-behaved turn that never actually exceeded its search budget.
_MAX_PAUSE_TURN_RETRIES = 6


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def call_tool(
        self, system: str, user: str, tool_name: str, tool_schema: dict, tool_description: str
    ) -> dict[str, Any]:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"name": tool_name, "description": tool_description, "input_schema": tool_schema}],
            tool_choice={"type": "tool", "name": tool_name},
        )
        if response.stop_reason == "max_tokens":
            raise RuntimeError(
                "The model's response was cut off before it finished, likely because the posting is unusually "
                "long or dense. Try trimming the posting text and analyzing again."
            )
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input
        raise RuntimeError(f"Model response did not include a call to tool '{tool_name}'")

    def call_tool_with_search(
        self,
        system: str,
        user: str,
        tool_name: str,
        tool_schema: dict,
        tool_description: str,
        max_searches: int = 2,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        tools = [
            {"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches},
            {"name": tool_name, "description": tool_description, "input_schema": tool_schema},
        ]
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        search_actions: list[dict[str, Any]] = []

        for _ in range(_MAX_PAUSE_TURN_RETRIES):
            response = self._client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system,
                messages=messages,
                tools=tools,
                tool_choice={"type": "any"},
            )
            if response.stop_reason == "max_tokens":
                raise RuntimeError(
                    "The model's response was cut off before it finished, likely because the posting is unusually "
                    "long or dense. Try trimming the posting text and analyzing again."
                )

            pending_query: str | None = None
            for block in response.content:
                if block.type == "server_tool_use" and block.name == "web_search":
                    pending_query = block.input.get("query")
                elif block.type == "web_search_tool_result":
                    if pending_query is not None and isinstance(block.content, list):
                        results = [
                            {"title": r.title, "url": r.url}
                            for r in block.content
                            if getattr(r, "type", None) == "web_search_result"
                        ]
                        search_actions.append({"query": pending_query, "results": results})
                    pending_query = None
                elif block.type == "tool_use" and block.name == tool_name:
                    return block.input, search_actions

            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue

            raise RuntimeError(f"Model response did not include a call to tool '{tool_name}'")

        raise RuntimeError(f"Model response did not include a call to tool '{tool_name}' after retrying a paused turn")

    def fetch_url_text(self, url: str) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": f"Fetch the content at {url}"}],
            tools=[{"type": "web_fetch_20250910", "name": "web_fetch", "max_content_tokens": 50000}],
            tool_choice={"type": "tool", "name": "web_fetch"},
        )
        if response.stop_reason == "max_tokens":
            raise RuntimeError(
                "The fetch was cut off before it finished, likely because the page is unusually long or "
                "dense. Try pasting the posting text directly instead."
            )
        for block in response.content:
            if block.type != "web_fetch_tool_result":
                continue
            result = block.content
            if getattr(result, "type", None) == "web_fetch_tool_result_error":
                raise RuntimeError("Could not fetch this URL. Try pasting the posting text directly instead.")
            source = result.content.source
            if getattr(source, "type", None) != "text":
                raise RuntimeError(
                    "This URL didn't return readable text content. Try pasting the posting text directly instead."
                )
            return source.data
        raise RuntimeError("Could not fetch content from this URL. Try pasting the posting text directly instead.")
