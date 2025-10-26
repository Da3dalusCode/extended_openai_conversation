from __future__ import annotations

DOMAIN = "extended_openai_conversation"
CONFIG_ENTRY_VERSION = 2

# Core config fields
CONF_BASE_URL = "base_url"
CONF_API_VERSION = "api_version"
CONF_ORGANIZATION = "organization"
CONF_CHAT_MODEL = "chat_model"

# Strategy toggles
CONF_USE_RESPONSES_API = "use_responses_api"
CONF_MODEL_STRATEGY = "model_strategy"
MODEL_STRATEGY_AUTO = "auto"
MODEL_STRATEGY_FORCE_CHAT = "force_chat_completions"
MODEL_STRATEGY_FORCE_RESPONSES = "force_responses_api"

# Sampling / limits
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_MAX_TOKENS = "max_tokens"
CONF_REASONING_EFFORT = "reasoning_effort"  # minimal|low|medium|high

# Services
SERVICE_QUERY_IMAGE = "query_image"

# Defaults
DEFAULT_CHAT_MODEL = "gpt-5"
DEFAULT_USE_RESPONSES_API = True
DEFAULT_MODEL_STRATEGY = MODEL_STRATEGY_AUTO
DEFAULT_TEMPERATURE = 0.4
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TOKENS = 300
DEFAULT_REASONING_EFFORT = "medium"

DEFAULT_PROMPT = (
    "You are a helpful assistant connected to Home Assistant. Keep replies brief. "
    "When you plan to call Home Assistant services, prefer to do so directly via "
    "Assist pipelines; your response text should still summarize the result."
)
