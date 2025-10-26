"""Constants for Extended OpenAI Conversation (EOC)."""

from __future__ import annotations

# Re-export HA's standard keys so other modules can import from our const safely.
from homeassistant.const import CONF_API_KEY, CONF_NAME  # noqa: F401

# Domain & entry version
DOMAIN = "extended_openai_conversation"
CONFIG_ENTRY_VERSION = 3

# Base / auth
CONF_BASE_URL = "base_url"                # e.g., https://api.openai.com/v1
CONF_API_VERSION = "api_version"          # Azure OpenAI API version (optional)
CONF_ORGANIZATION = "organization"        # OpenAI org (optional)
CONF_CHAT_MODEL = "chat_model"

# Strategy
CONF_USE_RESPONSES_API = "use_responses_api"
CONF_MODEL_STRATEGY = "model_strategy"    # 'auto' | 'force_chat_completions' | 'force_responses_api'
MODEL_STRATEGY_AUTO = "auto"
MODEL_STRATEGY_FORCE_CHAT = "force_chat_completions"
MODEL_STRATEGY_FORCE_RESPONSES = "force_responses_api"

# Reasoning
CONF_REASONING_EFFORT = "reasoning_effort"  # minimal | low | medium | high

# Sampling / limits
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_MAX_TOKENS = "max_tokens"

# Optional scaffolding (off by default)
CONF_MEMORY_ENABLED = "memory_enabled"
CONF_MEMORY_DEFAULT_NAMESPACE = "memory_default_namespace"
SERVICE_QUERY_IMAGE = "query_image"

# Defaults
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_API_VERSION = ""                  # only needed for Azure OpenAI
DEFAULT_CHAT_MODEL = "gpt-5"
DEFAULT_USE_RESPONSES_API = True
DEFAULT_MODEL_STRATEGY = MODEL_STRATEGY_AUTO
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_TEMPERATURE = 0.4
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TOKENS = 300
DEFAULT_PROMPT = ""
DEFAULT_MEMORY_ENABLED = False
DEFAULT_MEMORY_DEFAULT_NAMESPACE = "default"
