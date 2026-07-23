from types import SimpleNamespace
from unittest.mock import patch

import pytest

from job_scanner.llm_client import LLMClient


def test_call_tool_returns_tool_input_when_model_calls_the_tool():
    client = LLMClient(api_key="test-key")
    fake_block = SimpleNamespace(type="tool_use", name="my_tool", input={"foo": "bar"})
    fake_response = SimpleNamespace(content=[fake_block])

    with patch.object(client._client.messages, "create", return_value=fake_response) as mock_create:
        result = client.call_tool(system="sys", user="usr", tool_name="my_tool", tool_schema={"type": "object"})

    assert result == {"foo": "bar"}
    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args
    assert kwargs["tool_choice"] == {"type": "tool", "name": "my_tool"}


def test_call_tool_raises_when_model_does_not_call_the_tool():
    client = LLMClient(api_key="test-key")
    fake_response = SimpleNamespace(content=[SimpleNamespace(type="text", text="I refuse.")])

    with patch.object(client._client.messages, "create", return_value=fake_response):
        with pytest.raises(RuntimeError):
            client.call_tool(system="sys", user="usr", tool_name="my_tool", tool_schema={"type": "object"})
