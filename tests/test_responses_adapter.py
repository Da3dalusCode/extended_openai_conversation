import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "extended_openai_conversation"
    / "responses_adapter.py"
)

spec = importlib.util.spec_from_file_location(
    "responses_adapter", MODULE_PATH
)
responses_adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(responses_adapter)
responses_to_chat_like = responses_adapter.responses_to_chat_like


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.output_text = payload.get("output_text")

    def model_dump(self):
        # Return a deep copy to emulate pydantic behaviour
        return json.loads(json.dumps(self._payload))


@pytest.mark.parametrize(
    "payload, expected_text, has_tools",
    [
        (
            {
                "id": "resp_123",
                "model": "gpt-5-mini",
                "output": [
                    {
                        "id": "msg_1",
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Hello home!"}],
                    }
                ],
                "usage": {"input_tokens": 5, "output_tokens": 7},
            },
            "Hello home!",
            False,
        ),
        (
            {
                "id": "resp_tool",
                "model": "gpt-5-mini",
                "output": [
                    {
                        "id": "msg_1",
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "toolu_1",
                                "name": "execute_service",
                                "input": {
                                    "domain": "rest_command",
                                    "service": "memory_write",
                                    "service_data": {"content": "remember this"},
                                },
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 20, "output_tokens": 2, "total_tokens": 22},
            },
            None,
            True,
        ),
    ],
)
def test_responses_normalization(payload, expected_text, has_tools):
    response = DummyResponse(payload)
    normalised = responses_to_chat_like(response)

    assert normalised["object"] == "chat.completion"
    assert normalised["id"] == payload["id"]

    choice = normalised["choices"][0]
    message = choice["message"]

    if expected_text is not None:
        assert message["content"] == expected_text
    else:
        assert message["content"] is None

    if has_tools:
        assert choice["finish_reason"] == "tool_calls"
        assert message["tool_calls"]
        tool_call = message["tool_calls"][0]
        assert tool_call["function"]["name"] == "execute_service"
        arguments = json.loads(tool_call["function"]["arguments"])
        assert arguments["domain"] == "rest_command"
    else:
        assert choice["finish_reason"] == "stop"
        assert "tool_calls" not in message

    usage = normalised.get("usage")
    assert usage is not None
    assert "total_tokens" in usage
