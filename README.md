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
  - No `temperature/top_p` on reasoning endpoints :contentReference[oaicite:14]{index=14}  
- **Chat Completions** for non‑reasoning models (sampling allowed)  
- **Options gear** (model, strategy, effort, max tokens, temp/top‑p, prompt) via `OptionsFlowWithReload` :contentReference[oaicite:15]{index=15}  
- **Azure OpenAI** support (Base URL + API version) :contentReference[oaicite:16]{index=16}  
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
- **Model** (default `gpt-5`)  
- **Model strategy**: `auto` \| `force_chat_completions` \| `force_responses_api`  
- **Use Responses API** (for non‑reasoning models when strategy is `auto`)  
- **Reasoning effort**: `minimal` \| `low` \| `medium` \| `high`  
- **Max tokens**, **Temperature**, **Top‑p**, **System prompt**

### Recommended (long, smart chats)
- Model: `gpt-5`  
- Strategy: `auto`  
- Use Responses API: **on**  
- Effort: **medium** (raise to **high** as needed)  
- Max tokens: **800–1200**  
> With Responses API, *system text* goes into **`instructions`** and inputs use **`input_text`**. :contentReference[oaicite:17]{index=17}

## Assist usage
- **Settings → Voice Assistants** → set **Conversation agent** = *Extended OpenAI Conversation*  
- Use Assist (text/voice) or ESPHome satellites normally.  
- The agent returns `continue_conversation` when follow‑up is implied.

## Troubleshooting
- **400: invalid input type** (older builds): ensure you’re on v1.4.0+ (we use `input_text` + `instructions`). :contentReference[oaicite:18]{index=18}  
- **`intent-failed` with `.as_dict`**: fixed in v1.4.0 (compat shim). :contentReference[oaicite:19]{index=19}  
- **Blocking SSL warning (`load_verify_locations`)**: fixed by using HA’s shared HTTPX client in v1.4.0. :contentReference[oaicite:20]{index=20}

Enable debug:
```yaml
action: logger.set_level
data:
  custom_components.extended_openai_conversation: debug
  homeassistant.components.conversation: debug
