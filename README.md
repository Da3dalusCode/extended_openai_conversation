# Extended OpenAI Conversation (EOC)

A Home Assistant custom integration that extends the stock `openai_conversation` with:

- **GPT‑5** (reasoning models) via the **Responses API**
- Optional **`reasoning.effort`** (`low`, `medium`, `high`) for GPT‑5
- A clean, **non‑streaming** path that’s **Assist‑compatible** (stable result shape & `continue_conversation`)
- Deterministic system prompt assembly with a safe, straightforward tone
- Groundwork for a **local memory layer** (disabled by default)
- Router/MITM for tool calls (scaffolded; off by default)
- A single‑screen **Options UI** (no more blank “arrow” pages)

> ⚠️ **Statefulness**: Dialog **history is off** by default (stateless per turn). This release focuses on a robust core loop for voice and text. Memory/tools will follow once core reliability is rock solid.

---

## Requirements

- Home Assistant (recent version; tested on October 2025 builds)
- HACS for installation/updates
- An OpenAI‑compatible endpoint  
  - Default: `https://api.openai.com/v1`  
  - Works with Azure OpenAI / compatible gateways by setting **Base URL** and optional **API Version**
- An **OpenAI API key** (or compatible API)

---

## Install (HACS)

1. **HACS → Integrations → ⋮ → Custom repositories →** add your repo URL (category: *Integration*).
2. Search **Extended OpenAI Conversation** in HACS and **Install**.
3. **Restart Home Assistant**.

---

## Add & Configure (Home Assistant UI)

1. **Settings → Devices & Services → Add Integration →** search **Extended OpenAI Conversation**.
2. In the **setup form**, enter:
   - **API Key** (required)
   - **Base URL** (optional, default `https://api.openai.com/v1`)
   - **API Version** (Azure/compat only)
   - **Organization** (optional)
   - **Chat model** (e.g. `gpt-4o-mini` or a GPT‑5 model name)
   - **Model strategy** (`auto` / `force_chat` / `force_responses`)
   - **Use Responses API** (recommended **on** for GPT‑5)
   - **Reasoning effort** (empty/`low`/`medium`/`high` — **GPT‑5 only**)

3. Go to **Settings → Voice Assistants → [Your Assistant] → Conversation agent** and select **Extended OpenAI Conversation**.
4. (Optional) In the same screen toggle **Prefer handling commands locally** for faster on/off device control with Assist pipelines.

> You can revisit **Options** later from the EOC integration card (single screen).

---

## Options (reference)

> ⚠️ GPT‑5 reasoning models **ignore** `temperature`/`top_p`. EOC hides/suppresses them for GPT‑5 + Responses API.

| Group | Option | Key | Notes |
|---|---|---|---|
| Auth | API Key | `api_key` | Required at setup; editable in Options. |
| Endpoint | Base URL | `base_url` | Default `https://api.openai.com/v1`; set for Azure/compat. |
| Endpoint | API Version | `api_version` | Azure/compat only. |
| Endpoint | Organization | `organization` | Optional. |
| Model | Chat model | `chat_model` | e.g. `gpt-4o-mini`, `gpt-5-...`. |
| Model | Model strategy | `model_strategy` | `auto` / `force_chat` / `force_responses`. |
| Responses | Use Responses API | `use_responses_api` | **On** for GPT‑5. |
| Reasoning | Reasoning effort | `reasoning_effort` | `low`, `medium`, `high` (empty = unset). GPT‑5 only. |
| Gen | Enable streaming | `enable_streaming` | Non‑streaming is **default**; streaming path will return later. |
| Gen | Temperature | `temperature` | Ignored with GPT‑5 reasoning. |
| Gen | Top‑p | `top_p` | Ignored with GPT‑5 reasoning. |
| Gen | Max prompt tokens | `max_tokens` | Prompt budget (pre‑LLM). |
| Gen | Max completion tokens | `max_completion_tokens` | Output budget. |
| Persona | Prompt | `prompt` | System prompt assembly; defaults to safe voice tone. |
| Persona | Attach username | `attach_username` | Prefix user name for context. |
| Persona | Speak confirmation first | `speak_confirmation_first` | Voice UX preference. |
| Streaming | Stream min chars | `stream_min_chars` | Ignored when streaming is off. |
| Context | Context threshold | `context_threshold` | Token budgeting for prompt. |
| Context | Truncate strategy | `context_truncate_strategy` | `keep_latest` / `clear_all`. |
| Router | Use tools | `use_tools` | Scaffold only; **off** by default. |
| Router | Force tools | `router_force_tools` | Scaffold only. |
| Router | Search regex | `router_search_regex` | Scaffold only. |
| Router | Write regex | `router_write_regex` | Scaffold only. |
| Router | Max function calls | `max_function_calls_per_conversation` | Scaffold only. |
| Memory (scaffold) | Base URL, API key, etc. | `memory_*` | Present but **disabled** by default. |

---

## Usage Notes

- **Assist compatibility**: EOC returns a result shape compatible with the Assist pipeline (stable `response.speech.plain.speech` and `continue_conversation`).
- **GPT‑5**: Set **Use Responses API** on and pick a **gpt‑5*** model. You can set `reasoning.effort` to `low`/`medium`/`high`.
- **Temperature/top_p**: These **do not apply** to GPT‑5 reasoning models; EOC will omit them on those calls.
- **Stateless**: Each turn is independent (history off). The memory layer will arrive later.

---

## Troubleshooting

### “Config flow could not be loaded: Invalid handler specified”
- Ensure `custom_components/extended_openai_conversation/config_flow.py` **defines `class ConfigFlow(...)`** (exact name).
- Clear `__pycache__/` under the integration folder and **Restart Home Assistant**.

### “ImportError: cannot import name 'DEFAULT_*' from const”
- Make sure `custom_components/extended_openai_conversation/const.py` exports the `DEFAULT_*` constants (not just a dict).
- Replace the file with the one from the release and **Restart**.

### Enable debug logs (current HA)
- From the **EOC integration card** menu: **Enable debug logging**.
- And/or run **Developer Tools → Actions → Service: `logger.set_level`** with:
  ```yaml
  homeassistant.components.assist_pipeline: debug
  homeassistant.components.conversation: debug
  custom_components.extended_openai_conversation: debug
