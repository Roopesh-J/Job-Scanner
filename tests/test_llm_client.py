from types import SimpleNamespace
from unittest.mock import patch

import pytest

from job_scanner.llm_client import LLMClient


def test_call_tool_returns_tool_input_when_model_calls_the_tool():
    client = LLMClient(api_key="test-key")
    fake_block = SimpleNamespace(type="tool_use", name="my_tool", input={"foo": "bar"})
    fake_response = SimpleNamespace(content=[fake_block], stop_reason="tool_use")

    with patch.object(client._client.messages, "create", return_value=fake_response) as mock_create:
        result = client.call_tool(
            system="sys", user="usr", tool_name="my_tool", tool_schema={"type": "object"}, tool_description="desc"
        )

    assert result == {"foo": "bar"}
    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args
    assert kwargs["tool_choice"] == {"type": "tool", "name": "my_tool"}


def test_call_tool_raises_when_model_does_not_call_the_tool():
    client = LLMClient(api_key="test-key")
    fake_response = SimpleNamespace(content=[SimpleNamespace(type="text", text="I refuse.")], stop_reason="end_turn")

    with patch.object(client._client.messages, "create", return_value=fake_response):
        with pytest.raises(RuntimeError):
            client.call_tool(
                system="sys", user="usr", tool_name="my_tool", tool_schema={"type": "object"}, tool_description="desc"
            )


def test_call_tool_raises_clear_error_when_response_is_truncated():
    client = LLMClient(api_key="test-key")
    fake_block = SimpleNamespace(type="tool_use", name="my_tool", input={"foo": "bar"})
    fake_response = SimpleNamespace(content=[fake_block], stop_reason="max_tokens")

    with patch.object(client._client.messages, "create", return_value=fake_response):
        with pytest.raises(RuntimeError, match="cut off"):
            client.call_tool(
                system="sys", user="usr", tool_name="my_tool", tool_schema={"type": "object"}, tool_description="desc"
            )


def test_call_tool_with_search_returns_tool_input_when_no_search_happens():
    client = LLMClient(api_key="test-key")
    fake_block = SimpleNamespace(type="tool_use", name="analyze_fit", input={"insights": []})
    fake_response = SimpleNamespace(content=[fake_block], stop_reason="tool_use")

    with patch.object(client._client.messages, "create", return_value=fake_response) as mock_create:
        tool_input, search_actions = client.call_tool_with_search(
            system="sys", user="usr", tool_name="analyze_fit", tool_schema={"type": "object"}, tool_description="desc"
        )

    assert tool_input == {"insights": []}
    assert search_actions == []
    _, kwargs = mock_create.call_args
    assert kwargs["tool_choice"] == {"type": "any"}
    tool_types = {t.get("type") for t in kwargs["tools"]}
    assert "web_search_20260209" in tool_types


def test_call_tool_with_search_captures_search_trace_before_final_tool_call():
    client = LLMClient(api_key="test-key")
    search_call = SimpleNamespace(type="server_tool_use", name="web_search", input={"query": "example query"})
    search_result_item = SimpleNamespace(
        type="web_search_result", title="Example Result", url="https://example.com/result"
    )
    search_result = SimpleNamespace(
        type="web_search_tool_result", tool_use_id="srvtoolu_1", content=[search_result_item]
    )
    final_call = SimpleNamespace(type="tool_use", name="analyze_fit", input={"insights": []})
    fake_response = SimpleNamespace(content=[search_call, search_result, final_call], stop_reason="tool_use")

    with patch.object(client._client.messages, "create", return_value=fake_response):
        tool_input, search_actions = client.call_tool_with_search(
            system="sys", user="usr", tool_name="analyze_fit", tool_schema={"type": "object"}, tool_description="desc"
        )

    assert tool_input == {"insights": []}
    assert search_actions == [
        {"query": "example query", "results": [{"title": "Example Result", "url": "https://example.com/result"}]}
    ]


def test_call_tool_with_search_proceeds_when_search_errors():
    client = LLMClient(api_key="test-key")
    search_call = SimpleNamespace(type="server_tool_use", name="web_search", input={"query": "example query"})
    search_error = SimpleNamespace(
        type="web_search_tool_result",
        tool_use_id="srvtoolu_1",
        content=SimpleNamespace(type="web_search_tool_result_error", error_code="max_uses_exceeded"),
    )
    final_call = SimpleNamespace(type="tool_use", name="analyze_fit", input={"insights": []})
    fake_response = SimpleNamespace(content=[search_call, search_error, final_call], stop_reason="tool_use")

    with patch.object(client._client.messages, "create", return_value=fake_response):
        tool_input, search_actions = client.call_tool_with_search(
            system="sys", user="usr", tool_name="analyze_fit", tool_schema={"type": "object"}, tool_description="desc"
        )

    assert tool_input == {"insights": []}
    assert search_actions == []


def test_call_tool_with_search_raises_when_final_tool_never_called():
    client = LLMClient(api_key="test-key")
    fake_response = SimpleNamespace(content=[SimpleNamespace(type="text", text="I'm done.")], stop_reason="end_turn")

    with patch.object(client._client.messages, "create", return_value=fake_response):
        with pytest.raises(RuntimeError):
            client.call_tool_with_search(
                system="sys", user="usr", tool_name="analyze_fit", tool_schema={"type": "object"}, tool_description="desc"
            )
