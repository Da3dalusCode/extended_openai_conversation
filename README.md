# Extended OpenAI Conversation (EOC) for Home Assistant

A maintained fork of **Extended OpenAI Conversation** that works with the **current Home Assistant**, the **OpenAI Python SDK 1.x**, and supports **reasoning‑class models** via the **Responses API** (future‑friendly beyond GPT‑5). Designed to plug directly into **Assist** (voice & text) with the correct response shape and optional memory scaffolding **off by default**.

> Upstream (reference): https://github.com/jekalmin/extended_openai_conversation  
> This fork (install via HACS): https://github.com/Da3dalusCode/extended_openai_conversation

---

## Features

- 🔊 **Assist integration** (voice & text): returns a valid `ConversationResult` and supports `continue_conversation`.
- 🧠 **Reasoning‑class models** (e.g., GPT‑5 series, o‑series) through the **Responses API**, including `reasoning: { effort: ... }`.
- 💬 **Standard models** through **Chat Completions** with `temperature` and `top_p`.
- 🧩 **Auto strategy** chooses the right API based on the model.
- 🧱 Memory/RAG scaffolding kept in the code but **OFF by default** (no external calls unless you wire it up).
- 🔐 Works with OpenAI or **OpenAI‑compatible** (including **Azure OpenAI**).

---

## Requirements

- Home Assistant **2024.6.0** or newer (recommended).
- An OpenAI API key (or Azure OpenAI key + endpoint + API version).
- HACS installed.

---

## Install (HACS)

1. In **HACS → Integrations**, add this repository as a **Custom repository** (if not using the default list):  
   `https://github.com/Da3dalusCode/extended_openai_conversation`
2. Install the integration.
3. **Restart Home Assistant.**
4. Go to **Settings → Devices & Services → Add Integration → “Extended OpenAI Conversation”**.
5. On the first screen, enter:
   - **API Key** (required)
   - **Base URL** (optional, required for Azure or other compatible servers)
   - **API Version** (Azure only)
   - **Organization** (optional)
   - **Default model** (e.g., `gpt-4o-mini`)

After creation, open **Options** to fine‑tune behavior.

---

## Options

- **Model**  
- **API Strategy**: `auto` (recommended), `force_chat`, `force_responses`  
- **Reasoning Effort** (reasoning models): `minimal | low | medium | high`  
- **Max Output Tokens** (mapped to `max_tokens`, `max_completion_tokens`, or `max_output_tokens` automatically)  
- **Temperature** / **Top‑p** (applied **only** to non‑reasoning models)  
- **System Prompt** (optional)

> **Important:** Reasoning models reject sampling parameters like `temperature` / `top_p`. This integration automatically omits them when using reasoning models.

---

## Azure OpenAI

- Set **Base URL** to your Azure endpoint (e.g., `https://YOUR_RESOURCE_NAME.openai.azure.com`).
- Set **API Version** (e.g., `2024-12-01-preview`).
- The **model** you specify should be the **deployment name** in Azure.

---

## Assist Tips

- “Prefer local handling” is configured in your **Voice Assistant** and is not modified by this integration.
- `continue_conversation` is set automatically when the assistant’s reply contains a follow‑up question.

---

## Troubleshooting

- **Can’t find the integration after install?** Restart Home Assistant, clear browser cache, and check **Logs**.
- **Invalid handler / migration errors?** Ensure you’ve restarted after installing/updating in HACS.
- **Reasoning model errors?** Use the **Responses API** (default in `auto`) and set **Reasoning Effort**. Do not set temperature/top‑p for reasoning models.

---

## Credits

- Original project: **jekalmin/extended_openai_conversation**
- This fork: **Da3dalusCode** — adds Responses API, reasoning support, and current HA compatibility.

