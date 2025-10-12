import importlib.util
from pathlib import Path
import json

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "extended_openai_conversation"
    / "responses_adapter.py"
)

SPEC = importlib.util.spec_from_file_location("responses_adapter", MODULE_PATH)
responses_adapter = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(responses_adapter)

responses_to_chat_like = responses_adapter.responses_to_chat_like


def test_responses_adapter_plain_text_normalisation():
    payload = {
        "id": "resp_123",
        "object": "response",
        "model": "gpt-5.1",
        "output": [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Hello from responses!",
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        },
    }

    chat_completion = responses_to_chat_like(payload)

    choice = chat_completion["choices"][0]
    message = choice["message"]
    assert message["content"] == "Hello from responses!"
    assert message.get("tool_calls") in (None, [])
    assert choice["finish_reason"] == "stop"
    assert chat_completion["usage"]["prompt_tokens"] == 10
    assert chat_completion["usage"]["completion_tokens"] == 20
    assert chat_completion["usage"]["total_tokens"] == 30
def test_responses_adapter_single_tool_call():
    payload = {
        "id": "resp_456",
        "object": "response",
        "model": "gpt-5.1",
        "output": [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_call",
                        "tool_call": {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "execute_service",
                                "arguments": {
                                    "domain": "rest_command",
                                    "service": "memory_write",
                                    "service_data": {
                                        "content": "Remember this fact"
                                    },
                                },
                            },
                        },
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": 5,
            "output_tokens": 10,
            "total_tokens": 15,
        },
    }

    chat_completion = responses_to_chat_like(payload)

    tool_calls = chat_completion["choices"][0]["message"]["tool_calls"]
    assert tool_calls
    assert len(tool_calls) == 1
    call = tool_calls[0]
    assert call["type"] == "function"
    assert call["function"]["name"] == "execute_service"
    arguments = json.loads(call["function"]["arguments"])
    assert arguments["domain"] == "rest_command"
    assert arguments["service"] == "memory_write"
    assert arguments["service_data"]["content"] == "Remember this fact"
    assert chat_completion["choices"][0]["message"]["content"] is None
    assert chat_completion["choices"][0]["finish_reason"] == "tool_calls"
    assert chat_completion["usage"]["prompt_tokens"] == 5
    assert chat_completion["usage"]["completion_tokens"] == 10
    assert chat_completion["usage"]["total_tokens"] == 15

