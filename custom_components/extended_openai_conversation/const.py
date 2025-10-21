# custom_components/extended_openai_conversation/const.py
from __future__ import annotations

DOMAIN = "extended_openai_conversation"

# ----- Config entry versioning (major/minor) -----
CONFIG_ENTRY_VERSION = 1
CONFIG_ENTRY_MINOR_VERSION = 0  # bump when you make backward-compatible data tweaks

# ----- Core auth / API settings -----
CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_API_VERSION = "api_version"
CONF_ORGANIZATION = "organization"
CONF_CHAT_MODEL = "chat_model"

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_CHAT_MODEL = "gpt-5"
DEFAULT_API_VERSION = ""

# ----- Model strategy + Responses API -----
CONF_MODEL_STRATEGY = "model_strategy"            # "auto" | "force_chat" | "force_responses"
MODEL_STRATEGY_AUTO = "auto"
MODEL_STRATEGY_FORCE_CHAT = "force_chat"
MODEL_STRATEGY_FORCE_RESPONSES = "force_responses"

CONF_USE_RESPONSES_API = "use_responses_api"      # bool

# ----- Reasoning effort -----
CONF_REASONING_EFFORT = "reasoning_effort"        # "low" | "medium" | "high"
REASONING_EFFORT_LOW = "low"
REASONING_EFFORT_MEDIUM = "medium"
REASONING_EFFORT_HIGH = "high"
REASONING_EFFORT_ALLOWED = {REASONING_EFFORT_LOW, REASONING_EFFORT_MEDIUM, REASONING_EFFORT_HIGH}

# ----- Streaming + sampling -----
CONF_ENABLE_STREAMING = "enable_streaming"        # bool
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"

# Tokens
CONF_MAX_TOKENS = "max_tokens"                    # responses API return tokens
CONF_MAX_COMPLETION_TOKENS = "max_completion_tokens"  # chat.completions fallback

# ----- Context handling -----
CONF_CONTEXT_THRESHOLD = "context_threshold"
CONF_CONTEXT_TRUNCATE_STRATEGY = "context_truncate_strategy"  # "keep_latest" | "clear_all"

TRUNCATE_KEEP_LATEST = "keep_latest"
TRUNCATE_CLEAR_ALL = "clear_all"

# ----- Misc conversation behaviors -----
CONF_ATTACH_USERNAME = "attach_username"
CONF_SPEAK_CONFIRMATION_FIRST = "speak_confirmation_first"
CONF_STREAM_MIN_CHARS = "stream_min_chars"
CONF_PROMPT = "prompt"

# ----- Router / memory tooling knobs (kept for future use, safe defaults) -----
CONF_ROUTER_FORCE_TOOLS = "router_force_tools"
CONF_ROUTER_SEARCH_REGEX = "router_search_regex"
CONF_ROUTER_WRITE_REGEX = "router_write_regex"
CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION = "max_function_calls_per_conversation"

# Budgets (token budgeting if enabled later)
CONF_BUDGET_PROFILE = "budget_profile"
CONF_BUDGET_RETRIEVED = "budget_retrieved"
CONF_BUDGET_SCRATCHPAD = "budget_scratchpad"

# Memory service (placeholder constants so optional modules can import safely)
CONF_MEMORY_BASE_URL = "memory_base_url"
CONF_MEMORY_WRITE_PATH = "memory_write_path"
CONF_MEMORY_SEARCH_PATH = "memory_search_path"
CONF_MEMORY_ASK_PATH = "memory_ask_path"

DEFAULT_MEMORY_WRITE_PATH = "/memories/write"
DEFAULT_MEMORY_SEARCH_PATH = "/memories/search"
DEFAULT_MEMORY_ASK_PATH = "/memories/ask"

# ----- Service names / attrs (compat shims to stop import errors) -----
SERVICE_QUERY_IMAGE = "query_image"
CONF_PAYLOAD_TEMPLATE = "payload_template"
EVENT_AUTOMATION_REGISTERED = "extended_openai_conversation_automation_registered"

ATTR_IMAGES = "images"
ATTR_PROMPT = "prompt"
ATTR_RESPONSE = "response"

# Reasonable defaults mirrored from your UI
DEFAULTS = {
    CONF_MODEL_STRATEGY: MODEL_STRATEGY_AUTO,
    CONF_USE_RESPONSES_API: True,
    CONF_REASONING_EFFORT: REASONING_EFFORT_LOW,
    CONF_ENABLE_STREAMING: False,
    CONF_TEMPERATURE: 0.3,
    CONF_TOP_P: 1.0,
    CONF_MAX_TOKENS: 320,
    CONF_MAX_COMPLETION_TOKENS: 320,
    CONF_CONTEXT_THRESHOLD: 13000,
    CONF_CONTEXT_TRUNCATE_STRATEGY: TRUNCATE_KEEP_LATEST,
    CONF_ATTACH_USERNAME: False,
    CONF_SPEAK_CONFIRMATION_FIRST: False,
    CONF_STREAM_MIN_CHARS: 90,
    CONF_ROUTER_FORCE_TOOLS: False,
    CONF_ROUTER_SEARCH_REGEX: r"^(what'?s my|what is my|do you remember|what did)",
    CONF_ROUTER_WRITE_REGEX: r"^(remember|save|note that|add to memory)\b",
    CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION: 1,
    CONF_BUDGET_PROFILE: 250,
    CONF_BUDGET_RETRIEVED: 600,
    CONF_BUDGET_SCRATCHPAD: 200,
    CONF_MEMORY_BASE_URL: "",
    CONF_MEMORY_WRITE_PATH: DEFAULT_MEMORY_WRITE_PATH,
    CONF_MEMORY_SEARCH_PATH: DEFAULT_MEMORY_SEARCH_PATH,
    CONF_MEMORY_ASK_PATH: DEFAULT_MEMORY_ASK_PATH,
}
