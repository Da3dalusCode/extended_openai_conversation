"""Constants for the Extended OpenAI Conversation integration."""

DOMAIN = "extended_openai_conversation"
DEFAULT_NAME = "Extended OpenAI Conversation"

# --- Connection / Auth ---
CONF_API_KEY = "api_key"
CONF_ORGANIZATION = "organization"
CONF_BASE_URL = "base_url"
DEFAULT_CONF_BASE_URL = "https://api.openai.com/v1"
CONF_API_VERSION = "api_version"
CONF_SKIP_AUTHENTICATION = "skip_authentication"
DEFAULT_SKIP_AUTHENTICATION = False

# --- Events (compat with original EOC) ---
EVENT_AUTOMATION_REGISTERED = "automation_registered_via_extended_openai_conversation"
EVENT_CONVERSATION_FINISHED = "extended_openai_conversation.conversation.finished"

# --- Prompt / Persona ---
CONF_PROMPT = "prompt"
DEFAULT_PROMPT = (
    "You are a helpful Home Assistant companion. "
    "Be concise, safe, and act only when asked. "
    "Use tools only for actions the user requested. "
    "Prefer plain language. If unsure, ask a brief clarifying question."
)
CONF_ATTACH_USERNAME = "attach_username"
DEFAULT_ATTACH_USERNAME = True
CONF_SPEAK_CONFIRMATION_FIRST = "speak_confirmation_first"
DEFAULT_SPEAK_CONFIRMATION_FIRST = False
CONF_STREAM_MIN_CHARS = "stream_min_chars"
DEFAULT_STREAM_MIN_CHARS = 48

# --- Models & Strategies ---
CONF_CHAT_MODEL = "chat_model"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"

CONF_MODEL_STRATEGY = "model_strategy"
MODEL_STRATEGY_AUTO = "auto"
MODEL_STRATEGY_FORCE_CHAT = "force_chat"
MODEL_STRATEGY_FORCE_RESPONSES = "force_responses"
DEFAULT_MODEL_STRATEGY = MODEL_STRATEGY_AUTO

CONF_USE_RESPONSES_API = "use_responses_api"
DEFAULT_USE_RESPONSES_API = True  # GPT‑5 defaults

CONF_REASONING_EFFORT = "reasoning_effort"  # "", "low", "medium", "high"

# --- Generation controls ---
CONF_ENABLE_STREAMING = "enable_streaming"
DEFAULT_ENABLE_STREAMING = False
CONF_TEMPERATURE = "temperature"
DEFAULT_TEMPERATURE = 0.5
CONF_TOP_P = "top_p"
DEFAULT_TOP_P = 1.0
CONF_MAX_TOKENS = "max_tokens"
DEFAULT_MAX_TOKENS = 150
CONF_MAX_COMPLETION_TOKENS = "max_completion_tokens"

# --- Tools / Router ---
CONF_USE_TOOLS = "use_tools"
DEFAULT_USE_TOOLS = False
CONF_ROUTER_FORCE_TOOLS = "router_force_tools"
DEFAULT_ROUTER_FORCE_TOOLS = False
CONF_ROUTER_SEARCH_REGEX = "router_search_regex"
DEFAULT_ROUTER_SEARCH_REGEX = r"(search|look\s*up|find)"
CONF_ROUTER_WRITE_REGEX = "router_write_regex"
DEFAULT_ROUTER_WRITE_REGEX = r"(remember|save|note|store)"
CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION = "max_function_calls_per_conversation"
DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION = 1

# --- Truncation / Context ---
CONF_CONTEXT_THRESHOLD = "context_threshold"
DEFAULT_CONTEXT_THRESHOLD = 8192
CONF_CONTEXT_TRUNCATE_STRATEGY = "context_truncate_strategy"
DEFAULT_CONTEXT_TRUNCATE_STRATEGY = "keep_latest"  # or "clear_all"

# --- Budgets (placeholders; used when memory/RAG is on) ---
CONF_BUDGET_PROFILE = "budget_profile"
CONF_BUDGET_RETRIEVED = "budget_retrieved"
CONF_BUDGET_SCRATCHPAD = "budget_scratchpad"
DEFAULT_BUDGET_PROFILE = 0
DEFAULT_BUDGET_RETRIEVED = 0
DEFAULT_BUDGET_SCRATCHPAD = 0

# --- Proactivity (scaffold) ---
CONF_PROACTIVITY_ENABLED = "proactivity_enabled"
CONF_PROACTIVITY_K = "proactivity_k"
CONF_PROACTIVITY_MIN_SCORE = "proactivity_min_score"
DEFAULT_PROACTIVITY_ENABLED = False
DEFAULT_PROACTIVITY_K = 3
DEFAULT_PROACTIVITY_MIN_SCORE = 0.75

# --- Memory (scaffold) ---
CONF_MEMORY_BASE_URL = "memory_base_url"
CONF_MEMORY_API_KEY = "memory_api_key"
CONF_MEMORY_DEFAULT_NAMESPACE = "memory_default_namespace"
DEFAULT_MEMORY_DEFAULT_NAMESPACE = "home"
CONF_MEMORY_SEARCH_PATH = "memory_search_path"
CONF_MEMORY_WRITE_PATH = "memory_write_path"

# --- Misc (sometimes imported by agents) ---
CONF_NAME = "name"
