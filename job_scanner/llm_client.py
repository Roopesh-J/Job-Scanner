import os
from typing import Any

import anthropic

DEFAULT_MODEL = "claude-sonnet-5"


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
