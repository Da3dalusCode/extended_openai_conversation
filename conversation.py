"""Conversation platform for Extended OpenAI Conversation."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationEntityFeature,
    ConversationInput,
    agent,
    ChatLog,
)
from homeassistant.helpers import intent

from .const import (
    DOMAIN,
    CONF_API_KEY,
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
    MODEL_STRATEGY_AUTO,
    MODEL_STRATEGY_FORCE_CHAT,
    MODEL_STRATEGY_FORCE_RESPONSES,
)
from .openai_support import build_async_client
from .model_capabilities import detect_model_capabilities
from .responses_adapter import response_text_from_responses_result

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ExtendedOpenAIConversationEntity(hass, entry)])


class ExtendedOpenAIConversationEntity(ConversationEntity):
    """A conversation entity backed by OpenAI or compatible servers."""

    _attr_has_entity_name = True
    _attr_name = "Extended OpenAI Conversation"
    _attr_supported_features = ConversationEntityFeature.CONTROL
    _attr_supported_languages = "*"  # support all

    def __init__(self, hass, entry) -> None:
        self.hass = hass
        self.entry = entry

    @property
    def unique_id(self) -> Optional[str]:
        return self.entry.entry_id

    @property
    def name(self) -> str:
        return self.entry.title or "Extended OpenAI Conversation"

    async def async_prepare(self, language: str | None = None) -> None:
        """Optionally warm up anything; nothing to do."""

    async def _async_handle_message(
        self, user_input: ConversationInput, chat_log: ChatLog
    ) -> agent.ConversationResult:
        """Handle a message from Assist."""
        data = self.entry.data
        options = {**self._default_options(), **self.entry.options}

        api_key = data.get(CONF_API_KEY)
        base_url = data.get(CONF_BASE_URL)
        api_version = data.get(CONF_API_VERSION) or None
        organization = data.get(CONF_ORGANIZATION) or None

        model = options.get(CONF_CHAT_MODEL)
        caps = detect_model_capabilities(model)
        strategy = options.get(CONF_MODEL_STRATEGY)

        # Decide call path
        use_responses = (
            (strategy == MODEL_STRATEGY_FORCE_RESPONSES)
            or (strategy == MODEL_STRATEGY_AUTO and caps.is_reasoning)
            or (strategy == MODEL_STRATEGY_AUTO and options.get(CONF_USE_RESPONSES_API, True) and not caps.is_reasoning)
        )

        # Build client
        client = build_async_client(
            self.hass,
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            organization=organization,
        )

        # Compose messages
        sys_prompt = (options.get("prompt") or DEFAULT_PROMPT).strip()
        user_text = user_input.text

        if use_responses:
            # Responses API path; never send temperature/top_p with reasoning models.
            payload: dict[str, Any] = {
                "model": model,
                "input": [
                    {"role": "system", "content": [{"type": "text", "text": sys_prompt}]} if sys_prompt else None,
                    {"role": "user", "content": [{"type": "text", "text": user_text}]},
                ],
            }
            payload["input"] = [x for x in payload["input"] if x]  # drop Nones

            max_tokens = int(options.get(CONF_MAX_TOKENS) or DEFAULT_MAX_TOKENS)
            if max_tokens > 0:
                payload["max_output_tokens"] = max_tokens

            if caps.is_reasoning:
                effort = options.get(CONF_REASONING_EFFORT)
                payload["reasoning"] = {"effort": effort}

            try:
                result = await client.responses.create(**payload)  # type: ignore[arg-type]
                text = response_text_from_responses_result(result)
                cont = _should_continue(text)
                return _ok(text, user_input.language, user_input.conversation_id, cont)
            except Exception as err:  # convert to intent error
                _LOGGER.exception("Responses API failure: %s", err)
                return _err(str(err), user_input.language)

        # Chat Completions path
        messages = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_text})

        kwargs: dict[str, Any] = {"model": model, "messages": messages}

        # Token knobs: for reasoning models, Chat Completions expects max_completion_tokens
        max_tokens = int(options.get(CONF_MAX_TOKENS) or DEFAULT_MAX_TOKENS)
        if max_tokens > 0:
            kwargs["max_completion_tokens" if caps.is_reasoning else "max_tokens"] = max_tokens

        if caps.accepts_temperature:
            if (t := options.get(CONF_TEMPERATURE)) is not None:
                kwargs["temperature"] = float(t)
            if (p := options.get(CONF_TOP_P)) is not None:
                kwargs["top_p"] = float(p)

        try:
            result = await client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
            msg = result.choices[0].message
            text = msg.content or ""
            cont = _should_continue(text)
            return _ok(text, user_input.language, user_input.conversation_id, cont)
        except Exception as err:
            _LOGGER.exception("Chat Completions failure: %s", err)
            return _err(str(err), user_input.language)

    # ---- internal helpers ----

    def _default_options(self) -> dict[str, Any]:
        return {
            CONF_CHAT_MODEL: self.entry.options.get(CONF_CHAT_MODEL) or self.entry.data.get(CONF_CHAT_MODEL) or "gpt-4o-mini",
            CONF_MODEL_STRATEGY: self.entry.options.get(CONF_MODEL_STRATEGY) or MODEL_STRATEGY_AUTO,
            CONF_USE_RESPONSES_API: self.entry.options.get(CONF_USE_RESPONSES_API, True),
            CONF_TEMPERATURE: self.entry.options.get(CONF_TEMPERATURE, 0.4),
            CONF_TOP_P: self.entry.options.get(CONF_TOP_P, 1.0),
            CONF_MAX_TOKENS: self.entry.options.get(CONF_MAX_TOKENS, 300),
            CONF_REASONING_EFFORT: self.entry.options.get(CONF_REASONING_EFFORT, "medium"),
            "prompt": self.entry.options.get("prompt", DEFAULT_PROMPT),
        }


def _ok(text: str, language: Optional[str], conversation_id: Optional[str], cont: bool) -> agent.ConversationResult:
    response = intent.IntentResponse(language=language)
    response.async_set_speech(text or "")
    return agent.ConversationResult(
        conversation_id=conversation_id,
        response=response,
        continue_conversation=cont,
    )


def _err(msg: str, language: Optional[str]) -> agent.ConversationResult:
    response = intent.IntentResponse(language=language)
    response.async_set_speech(f"Sorry, I had a problem: {msg}")
    return agent.ConversationResult(
        conversation_id=None,
        response=response,
        continue_conversation=False,
    )


def _should_continue(text: str) -> bool:
    # Simple heuristic: if assistant asks a question, request follow-up
    return "?" in (text or "")
