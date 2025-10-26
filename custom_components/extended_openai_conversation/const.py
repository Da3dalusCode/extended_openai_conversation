"""Constants for Extended OpenAI Conversation (EOC)."""

from __future__ import annotations
from homeassistant.const import CONF_API_KEY, CONF_NAME  # re-export for safety

DOMAIN = "extended_openai_conversation"
CONFIG_ENTRY_VERSION = 3

# Base / auth
CONF_BASE_URL = "base_url"                 # e.g., https://api.openai.com/v1
CONF_API_VERSION = "api_version"           # Azure OpenAI (optional)
CONF_ORGANIZATION = "organization"         # OpenAI org (optional)
CONF_CHAT_MODEL = "chat_model"

# Strategy
CONF_USE_RESPONSES_API = "use_responses_api"
CONF_MODEL_STRATEGY = "model_strategy"     # auto | force_chat_completions | force_responses_api
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
CONF_FUNCTIONS_YAML = "functions"
CONF_ENABLE_WEB_SEARCH = "enable_web_search"
CONF_SEARCH_CONTEXT_SIZE = "search_context_size"
CONF_INCLUDE_HOME_LOCATION = "include_home_location"
CONF_MAX_TOOL_CALLS = "max_tool_calls"
CONF_ENABLE_MCP = "enable_mcp_tools"
CONF_MCP_TIMEOUT = "mcp_timeout"
CONF_MCP_MAX_PAYLOAD = "mcp_max_payload"

# Optional service
SERVICE_QUERY_IMAGE = "query_image"

# Defaults
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_API_VERSION = ""                   # Azure only
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
DEFAULT_ENABLE_WEB_SEARCH = False
DEFAULT_SEARCH_CONTEXT_SIZE = 8
DEFAULT_INCLUDE_HOME_LOCATION = False
DEFAULT_MAX_TOOL_CALLS = 4
DEFAULT_ENABLE_MCP = False
DEFAULT_MCP_TIMEOUT = 20
DEFAULT_MCP_MAX_PAYLOAD = 16384
