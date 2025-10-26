"""Conversation platform for Extended OpenAI Conversation."""

from __future__ import annotations

import json
from types import SimpleNamespace
import logging
from typing import Any, Optional, Literal

from homeassistant.components import conversation as ha_conversation
from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationEntityFeature,
    ChatLog,
    ConversationInput,
)
from homeassistant.components.homeassistant.exposed_entities import (
    async_should_expose,
)
from homeassistant.helpers import entity_registry as er, intent
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
from .responses_adapter import response_text_from_responses_result
from .tools_orchestrator import ToolExecutionContext, ToolError, ToolOrchestrator

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

        client = build_async_client(
            self.hass,
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            organization=organization,
        )

        sys_prompt = (options.get("prompt") or DEFAULT_PROMPT).strip()
        orchestrator = ToolOrchestrator(self.hass, options)
        context = ToolExecutionContext(
            hass=self.hass,
            user_input=user_input,
            exposed_entities=self._collect_exposed_entities(),
        )

        try:
            if use_responses:
                text, cont = await self._handle_with_responses_api(
                    client=client,
                    model=model,
                    user_input=user_input,
                    sys_prompt=sys_prompt,
                    caps=caps,
                    options=options,
                    orchestrator=orchestrator,
                    context=context,
                )
            else:
                text, cont = await self._handle_with_chat_completions(
                    client=client,
                    model=model,
                    user_input=user_input,
                    sys_prompt=sys_prompt,
                    caps=caps,
                    options=options,
                    orchestrator=orchestrator,
                    context=context,
                )
        except Exception as err:
            _LOGGER.exception("Conversation handling failed: %s", err)
            return _err(str(err), user_input.language)

        if not text:
            text = "I'm sorry, I couldn't produce a response."

        return _ok(
            text=text,
            language=user_input.language,
            conversation_id=user_input.conversation_id,
            cont=cont,
        )

    def _collect_exposed_entities(self) -> list[dict[str, Any]]:
        """Return all entities exposed to the conversation agent."""

        registry = er.async_get(self.hass)
        exposed: list[dict[str, Any]] = []
        for state in self.hass.states.async_all():
            entity_id = state.entity_id
            if not async_should_expose(self.hass, ha_conversation.DOMAIN, entity_id):
                continue
            entry = registry.async_get(entity_id)
            aliases = list(entry.aliases) if entry and entry.aliases else []
            exposed.append(
                {
                    "entity_id": entity_id,
                    "name": state.name,
                    "state": state.state,
                    "aliases": aliases,
                }
            )
        return exposed

    async def _handle_with_responses_api(
        self,
        *,
        client,
        model: str,
        user_input: ConversationInput,
        sys_prompt: str,
        caps,
        options: dict[str, Any],
        orchestrator: ToolOrchestrator,
        context: ToolExecutionContext,
    ) -> tuple[str, bool]:
        """Execute the Responses API interaction with tool-calling."""

        max_tokens = int(options.get(CONF_MAX_TOKENS) or DEFAULT_MAX_TOKENS)
        reasoning_effort = options.get(CONF_REASONING_EFFORT)

        tools_payload = orchestrator.responses_tools
        previous_response_id: str | None = None
        tool_outputs: list[dict[str, Any]] | None = None
        total_calls = 0
        first_request = True

        response = None

        while True:
            request: dict[str, Any] = {"model": model}
            if first_request:
                request["input"] = [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_input.text}],
                    }
                ]
                if sys_prompt:
                    request["instructions"] = sys_prompt
            else:
                request["previous_response_id"] = previous_response_id
                request["input"] = []
                if tool_outputs:
                    request["tool_outputs"] = tool_outputs

            if max_tokens > 0:
                request["max_output_tokens"] = max_tokens
            if caps.is_reasoning and reasoning_effort:
                request["reasoning"] = {"effort": reasoning_effort}

            if tools_payload:
                request["tools"] = tools_payload
                request["tool_choice"] = "auto"
                request["max_tool_calls"] = orchestrator.max_calls()

            response = await client.responses.create(**request)
            function_calls = _extract_responses_function_calls(response)

            if not function_calls:
                text = response_text_from_responses_result(response)
                if not text:
                    text = "I'm sorry, I wasn't able to produce a response."
                return text, _should_continue(text)

            tool_outputs = []
            for call in function_calls:
                tool_call_id = getattr(call, "call_id", None) or getattr(call, "id", "")
                try:
                    arguments = json.loads(call.arguments or "{}")
                except (TypeError, json.JSONDecodeError):
                    arguments = {}

                if total_calls >= orchestrator.max_calls():
                    tool_outputs.append(
                        {
                            "tool_call_id": tool_call_id,
                            "output": "Tool call limit reached; skipping execution.",
                        }
                    )
                    continue

                try:
                    tool_result = await orchestrator.execute_tool(
                        call.name, arguments, context
                    )
                except ToolError as err:
                    tool_result = f"Tool '{call.name}' failed: {err}"
                except Exception as err:  # pragma: no cover - defensive
                    tool_result = f"Tool '{call.name}' raised unexpected error: {err}"

                tool_outputs.append(
                    {"tool_call_id": tool_call_id, "output": tool_result}
                )
                total_calls += 1

            previous_response_id = response.id
            first_request = False
            tool_outputs = None

        return "", False

    async def _handle_with_chat_completions(
        self,
        *,
        client,
        model: str,
        user_input: ConversationInput,
        sys_prompt: str,
        caps,
        options: dict[str, Any],
        orchestrator: ToolOrchestrator,
        context: ToolExecutionContext,
    ) -> tuple[str, bool]:
        """Execute Chat Completions with tool-calling loop."""

        messages: list[dict[str, Any]] = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_input.text})

        kwargs: dict[str, Any] = {"model": model, "messages": messages}

        max_tokens = int(options.get(CONF_MAX_TOKENS) or DEFAULT_MAX_TOKENS)
        if max_tokens > 0:
            kwargs["max_completion_tokens" if caps.is_reasoning else "max_tokens"] = max_tokens

        if caps.accepts_temperature:
            if (t := options.get(CONF_TEMPERATURE)) is not None:
                kwargs["temperature"] = float(t)
            if (p := options.get(CONF_TOP_P)) is not None:
                kwargs["top_p"] = float(p)

        tool_specs = orchestrator.function_specs
        if tool_specs:
            kwargs["tools"] = [{"type": "function", "function": spec} for spec in tool_specs]
            kwargs["tool_choice"] = "auto"

        if orchestrator.supports_web_search():
            _LOGGER.debug(
                "Web search enabled, but Chat Completions route does not support hosted web search; skipping."
            )

        total_calls = 0

        while True:
            result = await client.chat.completions.create(**kwargs)
            choice = result.choices[0]
            message = choice.message
            finish_reason = choice.finish_reason

            if finish_reason in ("tool_calls", "function_call"):
                messages.append(message.model_dump(exclude_none=True))
                pending_calls = list(message.tool_calls or [])

                if message.function_call:
                    pending_calls.append(
                        _to_tool_call(message.function_call)
                    )

                if not pending_calls:
                    # No tool calls despite finish reason; break to avoid loop.
                    text = message.content or ""
                    return text, _should_continue(text)

                for call in pending_calls:
                    name = getattr(call.function, "name", None)
                    if not name:
                        continue

                    try:
                        arguments = json.loads(call.function.arguments or "{}")
                    except (TypeError, json.JSONDecodeError):
                        arguments = {}

                    if total_calls >= orchestrator.max_calls():
                        tool_result = "Tool call limit reached; skipping execution."
                    else:
                        try:
                            tool_result = await orchestrator.execute_tool(
                                name, arguments, context
                            )
                        except ToolError as err:
                            tool_result = f"Tool '{name}' failed: {err}"
                        except Exception as err:  # pragma: no cover - defensive
                            tool_result = f"Tool '{name}' raised unexpected error: {err}"
                        else:
                            total_calls += 1

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": name,
                            "content": tool_result,
                        }
                    )

                kwargs["messages"] = messages
                continue

            text = message.content or ""
            return text, _should_continue(text)

        return "", False

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


def _extract_responses_function_calls(response: Any) -> list[Any]:
    output = getattr(response, "output", None)
    if not output:
        return []
    calls: list[Any] = []
    for item in output:
        if getattr(item, "type", None) == "function_call":
            calls.append(item)
    return calls


def _to_tool_call(function_call: Any) -> SimpleNamespace:
    return SimpleNamespace(
        id=getattr(function_call, "id", ""),
        function=SimpleNamespace(
            name=getattr(function_call, "name", ""),
            arguments=getattr(function_call, "arguments", ""),
        ),
    )
