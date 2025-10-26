# Changelog

## [1.4.1] - 2025-10-26
### Added
- **Reasoning-model support via OpenAI Responses API** (e.g., GPT‑5 family). We now:
  - Send user text as `input_text` items  
  - Put the system prompt into `instructions`  
  - Add `reasoning: { effort }` only for reasoning-class models  
  - Avoid `temperature/top_p` on reasoning paths
- **Options UI (gear)** using `OptionsFlowWithReload`: model, strategy (`auto`, `force_chat_completions`, `force_responses_api`), reasoning effort, max tokens, temperature, top‑p, and system prompt.
- **Azure OpenAI** support (set Base URL + API version; the integration auto‑picks the Azure client).

### Fixed
- **Assist contract**: robust import shim for `ConversationResult` **with `.as_dict()`** so the agent manager can serialize results; resolves `intent-failed` caused by `AttributeError: ... as_dict`. :contentReference[oaicite:0]{index=0}
- **Responses API schema**: switched from `{"type": "text"}` to `{"type": "input_text"}` and moved the system prompt to `instructions`; removes 400s like:  
  `Invalid value: 'text'. Supported values are: 'input_text', 'input_image', ...`. :contentReference[oaicite:1]{index=1}
- **No more blocking SSL warning**: inject Home Assistant’s shared **HTTPX client** into the OpenAI SDK to prevent `load_verify_locations` from running in the event loop (warning previously pointed at `openai_support.py`). :contentReference[oaicite:2]{index=2}
- **Default model** updated to `gpt-5`.
- **Options gear visibility**: ensured `async_get_options_flow` is on the ConfigFlow class.
- Historical setup errors addressed during development:
  - Missing `supported_languages` abstract property (fixed). :contentReference[oaicite:3]{index=3}
  - Import of `CONF_API_KEY` from `const.py` (now re-exported and also imported from HA where appropriate). :contentReference[oaicite:4]{index=4}

### Notes
- Memory scaffolding remains present but **OFF by default**; no network calls unless explicitly enabled later.
- This is a **non‑breaking** upgrade from `1.3.x`.

[1.4.1]: https://github.com/Da3dalusCode/extended_openai_conversation/releases/tag/v1.4.1
