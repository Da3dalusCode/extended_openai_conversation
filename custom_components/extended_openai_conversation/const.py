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
CONF_MEMORY_BASE_URL = "memory_base_url"
CONF_MEMORY_API_KEY = "memory_api_key"
CONF_MEMORY_WRITE_PATH = "memory_write_path"
CONF_MEMORY_SEARCH_PATH = "memory_search_path"

# Toolbox / tools
CONF_FUNCTIONS = "functions"
CONF_FUNCTIONS_RAW = "functions_yaml"
CONF_MAX_TOOL_CALLS = "max_tool_calls"
CONF_MAX_TOOL_CHAIN = "max_tool_chain"
CONF_TOOL_TIMEOUT = "tool_timeout"
CONF_TOOL_MAX_OUTPUT_CHARS = "tool_max_output_chars"
CONF_ENABLE_WEB_SEARCH = "enable_web_search"
CONF_WEB_SEARCH_CONTEXT_SIZE = "web_search_context_size"
CONF_INCLUDE_HOME_LOCATION = "include_home_location"
CONF_ENABLE_MCP = "enable_mcp"
CONF_MCP_TIMEOUT = "mcp_timeout"
CONF_MCP_MAX_PAYLOAD = "mcp_max_payload"

WEB_SEARCH_CONTEXT_SIZE_SMALL = "small"
WEB_SEARCH_CONTEXT_SIZE_MEDIUM = "medium"
WEB_SEARCH_CONTEXT_SIZE_LARGE = "large"
WEB_SEARCH_CONTEXT_SIZE_PRESETS = {
    WEB_SEARCH_CONTEXT_SIZE_SMALL: 256,
    WEB_SEARCH_CONTEXT_SIZE_MEDIUM: 512,
    WEB_SEARCH_CONTEXT_SIZE_LARGE: 1024,
}

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
DEFAULT_MEMORY_BASE_URL = None
DEFAULT_MEMORY_API_KEY = None
DEFAULT_MEMORY_WRITE_PATH = "/v1/memory/write"
DEFAULT_MEMORY_SEARCH_PATH = "/v1/memory/search"
DEFAULT_FUNCTIONS: list[dict[str, object]] = [
    {
        "spec": {
            "name": "execute_service",
            "description": "Call one or more Home Assistant services on entities exposed to Assist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "list": {
                        "type": "array",
                        "description": "Service calls to execute in order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "Service domain, e.g. light or climate.",
                                },
                                "service": {
                                    "type": "string",
                                    "description": "The service to call within the domain.",
                                },
                                "service_data": {
                                    "type": "object",
                                    "description": "Service data including entity_id for an exposed entity.",
                                },
                            },
                            "required": ["domain", "service"],
                        },
                        "minItems": 1,
                    }
                },
                "required": ["list"],
            },
        },
        "function": {"type": "native", "name": "execute_service"},
    },
    {
        "spec": {
            "name": "add_automation",
            "description": "Append a YAML automation to automations.yaml and reload automations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_config": {
                        "type": "string",
                        "description": "YAML string describing the automation to add.",
                    }
                },
                "required": ["automation_config"],
            },
        },
        "function": {"type": "native", "name": "add_automation"},
    },
    {
        "spec": {
            "name": "get_history",
            "description": "Fetch recent state history for entities exposed to Assist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Entity IDs to query.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "ISO timestamp for the start of the window.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "ISO timestamp for the end of the window.",
                    },
                },
                "required": ["entity_ids"],
            },
        },
        "function": {"type": "native", "name": "get_history"},
    },
    {
        "spec": {
            "name": "rest",
            "description": "Perform an HTTP request via Home Assistant's REST data helper.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "HTTP or HTTPS endpoint to query.",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST"],
                        "description": "HTTP method (default GET).",
                    },
                    "headers": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "Optional request headers.",
                    },
                    "params": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "Optional query parameters.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds (default 10).",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional request body for POST.",
                    },
                },
                "required": ["url"],
            },
        },
        "function": {"type": "rest"},
    },
    {
        "spec": {
            "name": "scrape",
            "description": "Scrape structured text from a web page using a CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "HTTP or HTTPS page to scrape.",
                    },
                    "select": {
                        "type": "string",
                        "description": "CSS selector that locates the desired node.",
                    },
                    "attribute": {
                        "type": "string",
                        "description": "Optional attribute to read instead of text content.",
                    },
                    "index": {
                        "type": "integer",
                        "description": "Zero-based index when the selector matches multiple nodes.",
                    },
                },
                "required": ["url", "select"],
            },
        },
        "function": {"type": "scrape"},
    },
    {
        "spec": {
            "name": "script",
            "description": "Execute a Home Assistant script sequence or script entity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Home Assistant script steps to run.",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Existing script entity to run if no sequence is provided.",
                    },
                },
            },
        },
        "function": {"type": "script"},
    },
    {
        "spec": {
            "name": "template",
            "description": "Render a Home Assistant template with the provided arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "description": "Template string to render.",
                    },
                    "parse_json": {
                        "type": "boolean",
                        "description": "Parse the rendered template as JSON when true.",
                    },
                },
                "required": ["template"],
            },
        },
        "function": {"type": "template"},
    },
    {
        "spec": {
            "name": "composite",
            "description": "Run multiple tools sequentially, sharing variables between them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of tool invocations to execute in order.",
                    },
                },
                "required": ["sequence"],
            },
        },
        "function": {"type": "composite"},
    },
]
DEFAULT_FUNCTIONS_RAW = ""
DEFAULT_MAX_TOOL_CALLS = 4
DEFAULT_MAX_TOOL_CHAIN = 3
DEFAULT_TOOL_TIMEOUT = 12
DEFAULT_TOOL_MAX_OUTPUT_CHARS = 4000
DEFAULT_ENABLE_WEB_SEARCH = False
DEFAULT_WEB_SEARCH_CONTEXT_SIZE = WEB_SEARCH_CONTEXT_SIZE_MEDIUM
DEFAULT_INCLUDE_HOME_LOCATION = False
DEFAULT_ENABLE_MCP = False
DEFAULT_MCP_TIMEOUT = 8
DEFAULT_MCP_MAX_PAYLOAD = 4096
