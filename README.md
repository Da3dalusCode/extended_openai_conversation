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
- **Toolbox parity** with execute service / automation / history built-ins plus YAML-defined scripts, REST, scrape, template, composite helpers  
- **Hosted web search** toggle mirroring the stock OpenAI agent (Responses API + graceful chat fallback)  
- **Optional MCP bridge** that surfaces Home Assistant MCP servers as namespaced tools  
- **Azure OpenAI** support (Base URL + API version)  
- **Async‑safe client** using HA’s shared HTTPX to avoid blocking SSL CA loads

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
- **Model & Strategy** – choose default model plus routing strategy between Chat vs Responses API.  
- **Reasoning effort & token limits** – effort hint for reasoning models, max completion/output tokens, temperature & top‑p (chat only).  
- **Hosted Web Search** – enable OpenAI’s web search tool, set context size, optionally include approximate home location metadata.  
- **Toolbox limits** – cap total tool calls per user turn.  
- **MCP bridge** – opt‑in to surface any configured MCP servers (timeout + payload guardrails).  
- **Functions (YAML)** – edit the toolbox definition (defaults include `execute_service`, `add_automation`, `get_history`); append your own `rest`, `scrape`, `script`, `template`, or `composite` functions.

### Recommended (long, smart chats)
- Model: `gpt-5`  
- Strategy: `auto`  
- Use Responses API: **on**  
- Effort: **medium** (raise to **high** as needed)  
- Max tokens: **800–1200**  
> With Responses API, *system text* goes into **`instructions`** and inputs use **`input_text`**.

## Toolbox YAML quick reference
- Default entries provide `execute_service`, `add_automation`, and `get_history` using the historical EOC schema.  
- Append additional entries to expose `script`, `template`, `rest`, `scrape`, or `composite` actions.  
- Each entry requires a `spec` (tool definition shown to the model) and `function` (executor metadata); the existing [upstream examples](https://github.com/jekalmin/extended_openai_conversation/tree/main/examples/function) remain compatible.  
- Invalid YAML is rejected by the options flow and logged with context so setup continues safely.

## Assist usage
- **Settings → Voice Assistants** → set **Conversation agent** = *Extended OpenAI Conversation*  
- Use Assist (text/voice) or ESPHome satellites normally.  
- The agent returns `continue_conversation` when follow‑up is implied.

## Troubleshooting
- **400: invalid input type** (older builds): ensure you’re on v1.4.1+ (we use `input_text` + `instructions`). :contentReference[oaicite:8]{index=8}  
- **`intent-failed` with `.as_dict`**: fixed in v1.4.1 (compat shim). :contentReference[oaicite:9]{index=9}  
- **Blocking SSL warning (`load_verify_locations`)**: fixed by using HA’s shared HTTPX client in v1.4.1. :contentReference[oaicite:10]{index=10}

## Web search & MCP notes
- Web search is sent only on Responses API routes. For chat-only models we log a notice and the agent replies without search context.  
- MCP tools are surfaced when Home Assistant (or custom code) registers MCP servers under `hass.data["mcp_servers"]`; each tool call is sandboxed with timeout and payload limits.

Enable debug:
```yaml
action: logger.set_level
data:
  custom_components.extended_openai_conversation: debug
  homeassistant.components.conversation: debug
```

## Memory scaffolding
- Present but OFF by default (no network calls). When enabled in a future release, memory will write/query a provider and prepend retrieved context to instructions, following HA’s LLM guidance.
