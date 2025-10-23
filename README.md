# Extended OpenAI Conversation (EOC)

A maintained fork of **Extended OpenAI Conversation** for Home Assistant that:
- Works with current Home Assistant (tested on 2025.10.x).
- Uses **OpenAI Python SDK 1.x**.
- Adds first-class support for **OpenAI “reasoning-class” models** via the **Responses API** (e.g., GPT-5 family, o-series).  
  - Automatically sends `reasoning: { effort: ... }` to reasoning models.
  - **Does not** send `temperature`/`top_p` to reasoning models (they reject it).
- Keeps **memory/RAG scaffolding present but OFF by default**.
- Integrates cleanly with **Assist pipelines** (voice & text), returning the correct **ConversationResult** with `continue_conversation`.

> Upstream: https://github.com/jekalmin/extended_openai_conversation

---

## Installation (HACS)

1. In HACS, **Add custom repository**: `Da3dalusCode/extended_openai_conversation` (Integration).
2. Install the integration.
3. **Restart Home Assistant.**
4. Go to **Settings → Devices & Services → Add Integration → Extended OpenAI Conversation**.
5. On the first screen, enter your **OpenAI API key**.  
   - Set **Base URL** only if using an OpenAI-compatible endpoint (Azure/OpenAI-compatible, LocalAI, etc.).
6. After the integration is created, open **Options** to configure model/strategy.

### Quick test
Developer Tools → **Services** → `conversation.process`  
- `agent_id`: your EOC agent entity (e.g., `conversation.extended_openai_conversation`)  
- `text`: “What’s the weather like?”  
- Optional: set `conversation_id` to keep a thread.

---

## Configuration

### First-screen (Config Flow)
- **Name**: Integration title shown in HA
- **API Key** *(required)*
- **Base URL** *(optional; default `https://api.openai.com/v1`)*  
- **API Version / Organization** *(optional; for Azure or org scoping)*
- **Default Model** *(used initially; change later in Options)*

### Options (after install)
- **Model**: e.g., `gpt-4o-mini`, `gpt-5`, `o3-mini`
- **API strategy**:
  - `auto` (default): reasoning models → Responses API; others → Chat Completions
  - `force_chat`: always use Chat Completions
  - `force_responses`: always use Responses API
- **Reasoning effort**: minimal / low / medium / high (applies to reasoning models)
- **Temperature / Top-p**: only for non-reasoning models
- **Max output tokens**
- **System prompt**: optional system instructions

> **Tip:** If you want the default model to be a reasoning model (e.g., `gpt-5`), you can set it during setup or later in Options.

---

## How it works (routing)
- **Reasoning models** (e.g., GPT-5 family, o-series):  
  Calls **Responses API**, adds `reasoning: {effort}`, uses `max_output_tokens`, **omits** sampling params.
- **Non-reasoning models** (e.g., `gpt-4o-mini`):  
  Calls **Chat Completions**, uses `max_tokens` and standard sampling.

The conversation entity returns a **ConversationResult** with `intent.IntentResponse` so Assist speaks the reply and honors `continue_conversation`.

---

## Compatibility

- **Home Assistant**: 2024.10+ (tested on 2025.10.x)
- **OpenAI Python SDK**: `>=1.0.0,<2.0.0`
- **Endpoints**: OpenAI-hosted and Azure OpenAI-compatible

---

## Privacy & Security

- Your prompts go only to the configured endpoint (OpenAI or compatible).
- Don’t include secrets in prompts. Prefer network segmentation or environment isolation where appropriate.
- Memory/RAG scaffolding exists but is **off** in this release (no extra calls unless you wire them up).

---

## Troubleshooting

- **“Failed to set up” right after adding**:  
  Ensure you’re on the latest release. We include a compatibility shim for HA’s conversation API import differences. A restart is required after updating.
- **Reasoning model rejects temperature/top_p**:  
  Expected—those params are not sent on the reasoning path.
- **Assist bubble shows intent-failed**:  
  Check logs; verify your agent is the pipeline’s **Conversation agent** and that your API key is valid.

Enable debug for more detail:
```yaml
logger:
  logs:
    custom_components.extended_openai_conversation: debug

---

## Credits

-Upstream: jekalmin/extended_openai_conversation
-This fork: reasoning-model support, Responses API path, Assist compatibility updates.
