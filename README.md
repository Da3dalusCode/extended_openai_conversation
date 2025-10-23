# Extended OpenAI Conversation (EOC)
Reasoning-enabled fork of the upstream **Extended OpenAI Conversation** custom integration for Home Assistant.

- Works with **current Home Assistant (2025.x)** and **OpenAI Python SDK 1.x**
- Adds **Responses API** path for **reasoning-class models** (e.g., GPT-5 / o-series).  
  - Sends `reasoning: { effort: minimal/low/medium/high }` for reasoning models  
  - **Does not** send `temperature`/`top_p` to reasoning models  
- Uses **Chat Completions** path for non-reasoning models (where `temperature`/`top_p` apply)
- Clean **HACS → Restart → Add Integration** flow (first screen = API key)
- Integrates with **Assist** pipelines; returns the correct **ConversationResult** with `continue_conversation`
- **Memory/RAG scaffolding** remains present but **OFF by default**

> Upstream reference: https://github.com/jekalmin/extended_openai_conversation  
> This fork keeps the familiar UX but updates internals for modern OpenAI models.

---

## Installation (HACS)
1. In **HACS → Integrations → ⋮ → Custom repositories**, add  
   `https://github.com/Da3dalusCode/extended_openai_conversation` (Category: Integration).
2. Install **Extended OpenAI Conversation**.
3. **Restart Home Assistant**.
4. Go to **Settings → Devices & Services → Add Integration → Extended OpenAI Conversation**.
5. **Enter your OpenAI API key** (and **Base URL**/**API Version** if using Azure/OpenAI-compatible endpoints).
6. After setup completes, open the integration **Options** to fine-tune model behavior.
7. (Optional) In **Settings → Voice Assistants**, set your assistant’s **Conversation agent** to this integration.

> If you’re using Azure OpenAI, set **Base URL** to your Azure endpoint and **API Version** (e.g., `2024-12-01-preview`). The **model** value should be your **deployment name**.

---

## Options (recommended)
- **Model**: e.g., `gpt-4o-mini` (fast non-reasoning), `o3-mini` / `gpt-5-*` (reasoning).
- **API strategy**:  
  - `auto` → reasoning models go **Responses API**; others use **Chat Completions**  
  - `force_chat` → always use **Chat Completions**  
  - `force_responses` → always use **Responses API**
- **Reasoning effort**: `minimal | low | medium | high` (used only for reasoning-class models)
- **Temperature / Top-p**: **ignored** for reasoning; used on non-reasoning models
- **Max output tokens**: automatically mapped to the correct field:
  - **Responses** → `max_output_tokens`
  - **Chat Completions (reasoning)** → `max_completion_tokens`
  - **Chat Completions (non-reasoning)** → `max_tokens`
- **System prompt**: optional persona/instructions (memory is scaffolded but off by default)

---

## Troubleshooting
- **“Failed to set up” with `cannot import name 'agent'`**  
  Fixed in **v1.3.1** by importing `ConversationResult` from the correct module path.
- **Benign warning**: “blocking call to `import_module`… inside the event loop” – this comes from HA’s platform importer and is not fatal.
- **Enable debug logs**
  ```yaml
  # configuration.yaml
  logger:
    logs:
      custom_components.extended_openai_conversation: debug
- **Test quickly:** Developer Tools → Services → `conversation.process` → set `agent_id` to this integration’s entity.

## Privacy & Security
- Your prompts go to the configured endpoint (OpenAI or compatible).
- Don’t include secrets in prompts. Use network segmentation/environment isolation where appropriate.
- Memory/RAG endpoints exist in scaffolding but are **off** in this release.

## Compatibility
- Home Assistant **2024.10+** (tested on **2025.10.x**)
- OpenAI Python SDK **≥ 1.0.0 < 2.0.0**
- Supports OpenAI-hosted and Azure OpenAI-compatible endpoints.

## Credits
- Upstream: **jekalmin/extended_openai_conversation**
- This fork: reasoning-model support, Responses API path, Assist compatibility updates.

