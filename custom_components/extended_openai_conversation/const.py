"""Constants for Extended OpenAI Conversation (EOC)."""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY, CONF_NAME

# Domain
DOMAIN = "extended_openai_conversation"

# Config entry version & platforms
CONFIG_ENTRY_VERSION = 3

# Keys reused from HA
CONF_API_KEY = CONF_API_KEY  # type: ignore[no-redef]
CONF_NAME = CONF_NAME        # type: ignore[no-redef]

# Base / auth
CONF_BASE_URL = "base_url"                # e.g., https://api.openai.com/v1
CONF_API_VERSION = "api_version"          # Azure OpenAI API version
CONF_ORGANIZATION = "organization"
CONF_SKIP_AUTH = "skip_authentication"

# Model + strategy
CONF_CHAT_MODEL = "chat_model"
CONF_USE_RESPONSES_API = "use_responses_api"
CONF_MODEL_STRATEGY = "model_strategy"    # 'auto' | 'force_chat' | 'force_responses'
MODEL_STRATEGY_AUTO = "auto"
MODEL_STRATEGY_FORCE_CHAT = "force_chat"
MODEL_STRATEGY_FORCE_RESPONSES = "force_responses"

# Reasoning
CONF_REASONING_EFFORT = "reasoning_effort"  # minimal | low | medium | high

# Sampling
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"

# Limits
CONF_MAX_TOKENS = "max_tokens"  # User-facing single knob; we adapt to correct param
CONF_STREAM_MIN_CHARS = "stream_min_chars"
CONF_ENABLE_STREAMING = "enable_streaming"

# Prompt / memory scaffolding (kept but OFF by default)
CONF_PROMPT = "prompt"
CONF_MEMORY_ENABLED = "memory_enabled"
CONF_MEMORY_DEFAULT_NAMESPACE = "memory_default_namespace"

# Defaults
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_API_VERSION = ""  # Only needed for Azure OpenAI
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_MODEL_STRATEGY = MODEL_STRATEGY_AUTO
DEFAULT_USE_RESPONSES_API = True
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_TEMPERATURE = 0.4
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TOKENS = 300
DEFAULT_ENABLE_STREAMING = False
DEFAULT_STREAM_MIN_CHARS = 90
DEFAULT_PROMPT = ""
DEFAULT_MEMORY_ENABLED = False
DEFAULT_MEMORY_DEFAULT_NAMESPACE = "default"

# Data keys in hass.data
DATA_CLIENT = "client"
DATA_OPTIONS = "options"
