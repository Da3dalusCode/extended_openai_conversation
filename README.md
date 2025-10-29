# Extended OpenAI Conversation (EOC)

A maintained fork of **Extended OpenAI Conversation** for **Home Assistant** that:
- Works with **OpenAI Python SDK 1.x**
- Supports **reasoning‑class models** via the **Responses API** (e.g., GPT‑5 family)
- Integrates cleanly with **Assist pipelines**
- Keeps memory scaffolding present but **OFF by default**

- Upstream: https://github.com/jekalmin/extended_openai_conversation  
- This fork: https://github.com/Da3dalusCode/extended_openai_conversation

## Features
- **Assist‑compatible conversation entity** (returns current `ConversationResult`)  
- **Responses API** for reasoning models  
  - Inputs as `input_text` items  
  - System prompt in `instructions`  
  - `reasoning: { effort }` when applicable  
  - No `temperature/top_p` on reasoning endpoints
- **Chat Completions** for non‑reasoning models (sampling allowed)  
- **Options gear** (model, strategy, effort, max tokens, temp/top‑p, prompt) via `OptionsFlowWithReload`  
- **Azure OpenAI** support (Base URL + API version)  
- **Async‑safe client** using HA’s shared HTTPX to avoid blocking SSL CA loads
- **Toolbox parity** with upstream (service execution, automations, history, REST/scrape/script/template/composite when configured)
- **Hosted web search** hook for reasoning models with graceful chat fallback
- **Optional MCP bridge** (lazy import; safe no-op when library absent)
- **Tool execution limits** (per-call timeout, depth/call caps, chat log breadcrumbs for start/result)

## Requirements
- Home Assistant **2025.4.0+** recommended  
- Python OpenAI SDK **`>=1.0.0,<2.0.0`** (installed by HA from `manifest.json`)  
- HACS for installation

## Install (HACS)
1. HACS → *Custom repositories* → add this repo (category **Integration**)  
2. HACS → *Download* → **Restart Home Assistant** when prompted  
3. **Settings → Devices & Services → Add Integration →** “Extended OpenAI Conversation”  
4. Enter **API key** (set Base URL + API version for Azure)

## Configure
Open the integration card → **Configure** (gear):
- **Model** (default `gpt-5`)  
- **Model strategy**: `auto` \| `force_chat_completions` \| `force_responses_api`  
- **Use Responses API** (for non-reasoning models when strategy is `auto`)  
- **Reasoning effort**: `minimal` \| `low` \| `medium` \| `high`  
- **Max tokens**, **Temperature**, **Top‑p**, **System prompt**
- **Functions YAML**: list of tool specs (defaults cover service/automations/history); extend to add REST/scrape/script/template/composite entries.
- **Tool limits**: max tool calls/iterations, per-call timeout, response size cap.
- **Web search**: enable hosted search, context size (`small`/`medium`/`large` or raw token budget), optional approximate location sharing.
- **MCP bridge**: toggles + timeout/payload caps (requires [`mcp`](https://pypi.org/project/mcp/) to expose external tools).

### Toolbox
- Default toolbox exposes `execute_service`, `add_automation`, and `get_history`
- Extend via **Functions YAML** in options. Each entry:

```yaml
- spec:
    name: rest_weather
    description: Fetch the daily forecast from the weather API.
    parameters:
      type: object
      properties:
        city:
          type: string
  function:
    type: rest
    resource: https://api.example.com/forecast
    method: GET
    headers:
      Authorization: "{{ secrets.weather_token }}"
    payload_template: "{{ {'city': city} | tojson }}"
```

- `scrape` tool lazily imports `beautifulsoup4` (installed via manifest); if import fails at runtime the tool returns a friendly error without breaking the integration.
- Tool calls are capped per turn and per loop, with start/result breadcrumbs logged to the Assist chat log for auditability.

### Web search
- When `Enable hosted web search` is on, reasoning paths send the official `web_search` tool.
- Context size accepts `small`/`medium`/`large` or an integer budget (auto-mapped to low/medium/high).
- Optionally share approximate location (city/region/country/timezone) using HA config data.
- Chat Completions log a notice when the selected model lacks hosted search support and continue without failing.

### MCP bridge
- Disabled by default; toggle **Enable MCP bridge** to attempt discovery via the optional [`mcp`](https://pypi.org/project/mcp/) SDK.
- When the SDK is unavailable the bridge is a no-op. Future releases can hook into `MCPBridge` for richer behaviour.
- Timeout and payload caps prevent runaway external tool calls.

## Manual validation checklist
- Base conversation returns `ConversationResult` with language, `response_type`, and `continue_conversation` populated.
- `execute_service` honours Assist exposure; non-exposed entities return a readable denial.
- `get_history` responds with a concise summary (≤10 entries per entity).
- `rest` and `scrape` enforce per-call timeout/output caps; missing `beautifulsoup4` yields a graceful error.
- `composite` chains respect the orchestrator depth limit (safe failure message).
- Web search works end-to-end on reasoning models and logs a skip message on unsupported chat models.
- MCP bridge disabled → no change; when enabled (with SDK) tool discovery/execution routes through the orchestrator.
- Tool start/result breadcrumbs appear in the HA chat log for traceability.

### Recommended (long, smart chats)
- Model: `gpt-5`  
- Strategy: `auto`  
- Use Responses API: **on**  
- Effort: **medium** (raise to **high** as needed)  
- Max tokens: **800–1200**  
> With Responses API, *system text* goes into **`instructions`** and inputs use **`input_text`**.

## Assist usage
- **Settings → Voice Assistants** → set **Conversation agent** = *Extended OpenAI Conversation*  
- Use Assist (text/voice) or ESPHome satellites normally.  
- The agent returns `continue_conversation` when follow‑up is implied.

## Troubleshooting
- **400: invalid input type** (older builds): ensure you’re on v1.4.1+ (we use `input_text` + `instructions`). :contentReference[oaicite:8]{index=8}  
- **`intent-failed` with `.as_dict`**: fixed in v1.4.1 (compat shim). :contentReference[oaicite:9]{index=9}  
- **Blocking SSL warning (`load_verify_locations`)**: fixed by using HA’s shared HTTPX client in v1.4.1. :contentReference[oaicite:10]{index=10}

Enable debug:
```yaml
action: logger.set_level
data:
  custom_components.extended_openai_conversation: debug
  homeassistant.components.conversation: debug
```

## Memory scaffolding
- Present but OFF by default (no network calls). When enabled in a future release, memory will write/query a provider and prepend retrieved context to instructions, following HA’s LLM guidance.
