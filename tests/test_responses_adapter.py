import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "extended_openai_conversation" / "responses_adapter.py"
spec = importlib.util.spec_from_file_location("responses_adapter", MODULE_PATH)
responses_adapter = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(responses_adapter)  # type: ignore[assignment]

responses_to_chat_like = responses_adapter.responses_to_chat_like


class StubResponse:
    def __init__(self, payload, output_text=None):
        self._payload = payload
        self.output_text = output_text

    def model_dump(self):
        return self._payload


@pytest.mark.parametrize(
    "payload,expected_text,expected_tool_count",
    [
        (
            {
                "id": "resp_text",
                "model": "gpt-5-test",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": "Hello from Responses"}
                        ],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "created": 123,
            },
            "Hello from Responses",
            0,
        ),
        (
            {
                "id": "resp_tool",
                "model": "gpt-5-test",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_call",
                                "id": "call_1",
                                "tool_call": {
                                    "type": "function",
                                    "function": {
                                        "name": "execute_service",
                                        "arguments": {
                                            "domain": "rest_command",
                                            "service": "memory_write",
                                            "service_data": {
                                                "content": "remember this"
                                            },
                                        },
                                    },
                                },
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 12, "output_tokens": 0},
            },
            "",
            1,
        ),
        (
            {
                "id": "resp_nested",
                "model": "gpt-5-test",
                "response": {
                    "id": "resp_nested_inner",
                    "model": "gpt-5-test",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "Nested payload",
                                }
                            ],
                        }
                    ],
                    "usage": {"prompt_tokens": 4, "completion_tokens": 2},
                },
            },
            "Nested payload",
            0,
        ),
    ],
)
def test_responses_to_chat_like_shapes(payload, expected_text, expected_tool_count):
    response = StubResponse(payload)
    normalized = responses_to_chat_like(response)

    choice = normalized["choices"][0]
    message = choice["message"]

    assert message["content"] == expected_text
    tool_calls = message.get("tool_calls") or []
    assert len(tool_calls) == expected_tool_count

    if expected_tool_count:
        tool = tool_calls[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "execute_service"
        assert "service_data" in tool["function"]["arguments"]
        assert choice["finish_reason"] == "tool_calls"
    else:
        assert choice["finish_reason"] == "stop"

    usage = normalized["usage"]
    assert usage["prompt_tokens"] >= 0
    assert usage["completion_tokens"] >= 0
    assert usage["total_tokens"] >= 0
