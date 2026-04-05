"""
llm.py — LLM provider abstraction.

All pipeline stages call generate() here.
To swap providers (e.g. back to OpenAI), only this file needs to change.
"""

import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def generate(prompt: str, system: str = "", model: str = None, temperature: float = 0.0) -> str:
    """
    Send a prompt to the LLM and return the response text.

    Args:
        prompt:      The user message / main prompt.
        system:      Optional system message.
        model:       Model name. Defaults to ANTHROPIC_MODEL env var or claude-sonnet-4-6.
        temperature: Sampling temperature. Default 0.0 for reproducibility.

    Returns:
        Raw response string from the model.
    """
    model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    client = _get_client()

    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)

    return response.content[0].text
