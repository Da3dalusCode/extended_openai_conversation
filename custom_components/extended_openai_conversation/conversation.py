"""Conversation platform for Extended OpenAI Conversation."""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Optional, Literal

from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationEntityFeature,
    ChatLog,
)
from homeassistant.helpers import intent
from homeassistant.const import CONF_API_KEY

# Try to import the real ConversationResult; otherwise provide a compatible shim.
try:
    from homeassistant.components.conversation.agent import ConversationResult  # type: ignore[attr-defined]
except Exception:
    try:
        from homeassistant.components.conversation import agent as _agent_mod  # type: ignore[attr-defined]
        ConversationResult = _agent_mod.ConversationResult  # type: ignore[assignment]
    except Exception:

        class ConversationResult:  # type: ignore[misc]
            """Minimal shim consistent with HA's use of ConversationResult."""

            def __init__(self, *, conversation_id, response, continue_conversation) -> None:
                self.conversation_id = conversation_id
                self.response = response
                self.continue_conversation = continue_conversation

            def as_dict(self) -> dict[str, Any]:
                return {
                    "conversation_id": self.conversation_id,
                    "response": self.response,
                    "continue_conversation": self.continue_conversation,
                }

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_API_VERSION,
    CONF_ORGANIZATION,
    CONF_CHAT_MODEL,
    CONF_MODEL_STRATEGY,
    CONF_USE_RESPONSES_API,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_MAX_TOKENS,
    CONF_REASONING_EFFORT,
    DEFAULT_PROMPT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_USE_RESPONSES_API,
    MODEL_STRATEGY_AUTO,
    MODEL_STRATEGY_FORCE_CHAT,
    MODEL_STRATEGY_FORCE_RESPONSES,
)
from .model_capabilities import detect_model_capabilities
from .responses_adapter import (
    response_text_from_responses_result,
    extract_function_calls_from_response,
)
from .tools_orchestrator import ToolsOrchestrator, ToolExecutionError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ExtendedOpenAIConversationEntity(hass, entry)])


class ExtendedOpenAIConversationEntity(ConversationEntity):
    """A conversation entity backed by OpenAI or compatible servers."""

    _attr_has_entity_name = True
    _attr_name = "Extended OpenAI Conversation"
    _attr_supported_features = ConversationEntityFeature.CONTROL

    def __init__(self, hass, entry) -> None:
        self.hass = hass
        self.entry = entry

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return "*"

    @property
    def unique_id(self) -> Optional[str]:
        return self.entry.entry_id

    @property
    def name(self) -> str:
        return self.entry.title or "Extended OpenAI Conversation"

    async def async_prepare(self, language: str | None = None) -> None:
        """Optional prefetch/warm-up."""

    async def _async_handle_message(
        self, user_input: Any, chat_log: ChatLog
    ) -> ConversationResult:
        """Handle a message from Assist."""
        # Lazy import avoids SDK import at module load
        from .openai_support import build_async_client

        data = self.entry.data
        options = {**self._default_options(), **self.entry.options}

        api_key = data.get(CONF_API_KEY)
        base_url = data.get(CONF_BASE_URL)
        api_version = data.get(CONF_API_VERSION) or None
        organization = data.get(CONF_ORGANIZATION) or None

        model = options.get(CONF_CHAT_MODEL)
        caps = detect_model_capabilities(model)
        strategy = options.get(CONF_MODEL_STRATEGY)

        # Routing
        use_responses = (
            (strategy == MODEL_STRATEGY_FORCE_RESPONSES)
            or (strategy == MODEL_STRATEGY_AUTO and caps.is_reasoning)
        )
        if strategy == MODEL_STRATEGY_FORCE_CHAT:
            use_responses = False
        if strategy == MODEL_STRATEGY_AUTO and not caps.is_reasoning:
            if bool(options.get(CONF_USE_RESPONSES_API, DEFAULT_USE_RESPONSES_API)):
                use_responses = True

        _LOGGER.debug(
            "EOC: model=%s caps=%s strategy=%s use_responses=%s",
            model, caps, strategy, use_responses
        )

        orchestrator = ToolsOrchestrator(
            self.hass,
            options=options,
            chat_log=chat_log,
            agent_id=self.entity_id or DOMAIN,
        )
        orchestrator.reset()

        client = build_async_client(
            self.hass,
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            organization=organization,
        )

        sys_prompt = (options.get("prompt") or DEFAULT_PROMPT).strip()
        user_text = user_input.text

        if use_responses:
            try:
                responses_result = await self._run_responses_flow(
                    client=client,
                    model=model,
                    sys_prompt=sys_prompt,
                    user_text=user_text,
                    options=options,
                    caps=caps,
                    user_input=user_input,
                    orchestrator=orchestrator,
                )
            except ToolExecutionError as err:
                _LOGGER.warning("Responses tool failure: %s", err)
                return _err(str(err), user_input.language)
            except Exception as err:  # pragma: no cover - defensive guard
                _LOGGER.exception("Responses API failure: %s", err)
                return _err(str(err), user_input.language)

            text = response_text_from_responses_result(responses_result)
            cont = _should_continue(text)
            return _ok(
                text=text,
                language=user_input.language,
                conversation_id=user_input.conversation_id,
                cont=cont,
            )

        orchestrator.configure_chat_web_search(model)

        try:
            text = await self._run_chat_flow(
                client=client,
                model=model,
                sys_prompt=sys_prompt,
                user_text=user_text,
                options=options,
                caps=caps,
                user_input=user_input,
                orchestrator=orchestrator,
            )
        except ToolExecutionError as err:
            _LOGGER.warning("Chat tool failure: %s", err)
            return _err(str(err), user_input.language)
        except Exception as err:  # pragma: no cover
            _LOGGER.exception("Chat Completions failure: %s", err)
            return _err(str(err), user_input.language)

        cont = _should_continue(text)
        return _ok(
            text=text,
            language=user_input.language,
            conversation_id=user_input.conversation_id,
            cont=cont,
        )

    def _default_options(self) -> dict[str, Any]:
        return {
            CONF_CHAT_MODEL: self.entry.options.get(CONF_CHAT_MODEL)
            or self.entry.data.get(CONF_CHAT_MODEL)
            or "gpt-5",
            CONF_MODEL_STRATEGY: self.entry.options.get(CONF_MODEL_STRATEGY) or MODEL_STRATEGY_AUTO,
            CONF_USE_RESPONSES_API: self.entry.options.get(CONF_USE_RESPONSES_API, DEFAULT_USE_RESPONSES_API),
            CONF_TEMPERATURE: self.entry.options.get(CONF_TEMPERATURE, 0.4),
            CONF_TOP_P: self.entry.options.get(CONF_TOP_P, 1.0),
            CONF_MAX_TOKENS: self.entry.options.get(CONF_MAX_TOKENS, 300),
            CONF_REASONING_EFFORT: self.entry.options.get(CONF_REASONING_EFFORT, "medium"),
            "prompt": self.entry.options.get("prompt", DEFAULT_PROMPT),
        }

    async def _run_responses_flow(
        self,
        *,
        client,
        model: str,
        sys_prompt: str,
        user_text: str,
        options: dict[str, Any],
        caps,
        user_input,
        orchestrator: ToolsOrchestrator,
    ):
        payload: dict[str, Any] = {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                }
            ],
        }

        if sys_prompt:
            payload["instructions"] = sys_prompt

        max_tokens = int(options.get(CONF_MAX_TOKENS) or DEFAULT_MAX_TOKENS)
        if max_tokens > 0:
            payload["max_output_tokens"] = max_tokens

        if caps.is_reasoning:
            effort = options.get(CONF_REASONING_EFFORT)
            payload["reasoning"] = {"effort": effort}

        tools = orchestrator.conversation_tools_for_responses(self.hass)
        if tools:
            payload["tools"] = tools

        result = await client.responses.create(**payload)
        return await self._handle_responses_tool_calls(
            client=client,
            model=model,
            result=result,
            orchestrator=orchestrator,
            user_input=user_input,
        )

    async def _handle_responses_tool_calls(
        self,
        *,
        client,
        model: str,
        result,
        orchestrator: ToolsOrchestrator,
        user_input,
    ):
        depth = 0

        while True:
            calls = extract_function_calls_from_response(result)
            if not calls:
                return result

            outputs: list[dict[str, Any]] = []
            if depth >= orchestrator.max_chain_depth:
                for idx, call in enumerate(calls):
                    call_id = call.get("call_id") or call.get("id") or str(idx)
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": "Tool execution halted: maximum depth reached.",
                        }
                    )
                result = await client.responses.create(
                    model=model,
                    previous_response_id=getattr(result, "id", None),
                    input=outputs,
                )
                return result

            for call in calls:
                name = call.get("name")
                arguments = call.get("arguments")
                call_id = call.get("call_id") or call.get("id") or name
                if not name:
                    continue
                try:
                    output = await orchestrator.execute_tool_call(
                        name=name,
                        arguments=arguments,
                        user_input=user_input,
                        call_id=call_id,
                    )
                except ToolExecutionError as err:
                    output = f"Tool {name} failed: {err}"

                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id or (name or "unknown"),
                        "output": output,
                    }
                )

            if not outputs:
                return result

            result = await client.responses.create(
                model=model,
                previous_response_id=getattr(result, "id", None),
                input=outputs,
            )
            depth += 1

    async def _run_chat_flow(
        self,
        *,
        client,
        model: str,
        sys_prompt: str,
        user_text: str,
        options: dict[str, Any],
        caps,
        user_input,
        orchestrator: ToolsOrchestrator,
    ) -> str:
        messages: list[dict[str, Any]] = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_text})

        kwargs: dict[str, Any] = {"model": model, "messages": messages}

        max_tokens = int(options.get(CONF_MAX_TOKENS) or DEFAULT_MAX_TOKENS)
        if max_tokens > 0:
            key = "max_completion_tokens" if caps.is_reasoning else "max_tokens"
            kwargs[key] = max_tokens

        if caps.accepts_temperature:
            if (t := options.get(CONF_TEMPERATURE)) is not None:
                kwargs["temperature"] = float(t)
            if (p := options.get(CONF_TOP_P)) is not None:
                kwargs["top_p"] = float(p)

        tools = orchestrator.conversation_tools_for_chat()
        if tools:
            kwargs["tools"] = tools

        depth = 0
        while True:
            completion = await client.chat.completions.create(**kwargs)
            message = completion.choices[0].message
            content = message.content or ""
            tool_calls = getattr(message, "tool_calls", None) or []

            if not tool_calls:
                return content

            if depth >= orchestrator.max_chain_depth:
                suffix = "Tool chain limit reached; unable to continue."
                return f"{content}\n{suffix}" if content else suffix

            assistant_entry = {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    call.model_dump() if hasattr(call, "model_dump") else {
                        "id": getattr(call, "id", None),
                        "type": getattr(call, "type", "function"),
                        "function": {
                            "name": getattr(getattr(call, "function", None), "name", None),
                            "arguments": getattr(
                                getattr(call, "function", None), "arguments", "{}"
                            ),
                        },
                    }
                    for call in tool_calls
                ],
            }
            messages.append(assistant_entry)

            for call in tool_calls:
                call_id = getattr(call, "id", None)
                func = getattr(call, "function", None)
                call_name = getattr(func, "name", None)
                call_arguments = getattr(func, "arguments", "{}")
                if not call_name:
                    continue
                try:
                    output = await orchestrator.execute_tool_call(
                        name=call_name,
                        arguments=call_arguments,
                        user_input=user_input,
                        call_id=call_id,
                    )
                except ToolExecutionError as err:
                    output = f"Tool {call_name} failed: {err}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": output,
                    }
                )

            kwargs["messages"] = messages
            depth += 1


def _ok(*, text: str, language: Optional[str], conversation_id: Optional[str], cont: bool) -> ConversationResult:
    response = intent.IntentResponse(language=language)
    response.async_set_speech(text or "")
    return ConversationResult(
        conversation_id=conversation_id,
        response=response,
        continue_conversation=cont,
    )


def _err(msg: str, language: Optional[str]) -> ConversationResult:
    response = intent.IntentResponse(language=language)
    response.async_set_speech(f"Sorry, I had a problem: {msg}")
    return ConversationResult(
        conversation_id=None,
        response=response,
        continue_conversation=False,
    )


def _should_continue(text: str) -> bool:
    return "?" in (text or "")
